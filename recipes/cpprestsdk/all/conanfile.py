from conan import ConanFile
from conan.tools import files
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os

required_conan_version = ">=1.53.0"


class CppRestSDKConan(ConanFile):
    name = "cpprestsdk"
    description = "A project for cloud-based client-server communication in native code using a modern asynchronous " \
                  "C++ API design"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/Microsoft/cpprestsdk"
    topics = ("cpprestsdk", "rest", "client", "http", "https")
    license = "MIT"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_websockets": [True, False],
        "with_compression": [True, False],
        "pplx_impl": ["win", "winpplx"],
        "http_client_impl": ["winhttp", "asio"],
        "http_listener_impl": ["httpsys", "asio"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_websockets": True,
        "with_compression": True,
        "pplx_impl": "win",
        "http_client_impl": "winhttp",
        "http_listener_impl": "httpsys",
    }

    def export_sources(self):
        files.export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.pplx_impl
            del self.options.http_client_impl
            del self.options.http_listener_impl

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        self.requires("boost/1.80.0")
        self.requires("openssl/1.1.1s")
        if self.options.with_compression:
            self.requires("zlib/1.2.13")
        if self.options.with_websockets:
            self.requires("websocketpp/0.8.2")

    def package_id(self):
        self.info.requires["boost"].minor_mode()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        files.get(self, **self.conan_data["sources"][self.version],
                  destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # upstream CMakeLists.txt sets BUILD_SHARED_LIBS as a CACHE variable
        # remove for conan >=1.54.0
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0126"] = "NEW"
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_SAMPLES"] = False
        tc.variables["WERROR"] = False
        tc.variables["CPPREST_EXCLUDE_WEBSOCKETS"] = not self.options.with_websockets
        tc.variables["CPPREST_EXCLUDE_COMPRESSION"] = not self.options.with_compression
        if self.options.get_safe("pplx_impl"):
            tc.variables["CPPREST_PPLX_IMPL"] = self.options.pplx_impl
        if self.options.get_safe("http_client_impl"):
            tc.variables["CPPREST_HTTP_CLIENT_IMPL"] = self.options.http_client_impl
        if self.options.get_safe("http_listener_impl"):
            tc.variables["CPPREST_HTTP_LISTENER_IMPL"] = self.options.http_listener_impl
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_clang_libcxx(self):
        if self.settings.compiler == 'clang' and str(self.settings.compiler.libcxx) in ['libstdc++', 'libstdc++11']:
            files.replace_in_file(self, os.path.join(self.source_folder, 'Release', 'CMakeLists.txt'),
                                  'libc++', 'libstdc++')

    def build(self):
        files.apply_conandata_patches(self)
        self._patch_clang_libcxx()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        files.copy(self, "license.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        files.rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        files.rmdir(self, os.path.join(self.package_folder, "lib", "cpprestsdk"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpprestsdk")

        # cpprestsdk_boost_internal
        self.cpp_info.components["cpprestsdk_boost_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_boost_internal")
        self.cpp_info.components["cpprestsdk_boost_internal"].includedirs = []
        self.cpp_info.components["cpprestsdk_boost_internal"].requires = ["boost::boost"]
        # cpprestsdk_openssl_internal
        self.cpp_info.components["cpprestsdk_openssl_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_openssl_internal")
        self.cpp_info.components["cpprestsdk_openssl_internal"].includedirs = []
        self.cpp_info.components["cpprestsdk_openssl_internal"].requires = ["openssl::openssl"]
        # cpprest
        self.cpp_info.components["cpprest"].set_property("cmake_target_name", "cpprestsdk::cpprest")
        self.cpp_info.components["cpprest"].libs = files.collect_libs(self)
        self.cpp_info.components["cpprest"].requires = ["cpprestsdk_boost_internal", "cpprestsdk_openssl_internal"]
        if self.settings.os == "Linux":
            self.cpp_info.components["cpprest"].system_libs.append("pthread")
        elif self.settings.os == "Windows":
            if self.options.get_safe("http_client_impl") == "winhttp":
                self.cpp_info.components["cpprest"].system_libs.append("winhttp")
            if self.options.get_safe("http_listener_impl") == "httpsys":
                self.cpp_info.components["cpprest"].system_libs.append("httpapi")
            self.cpp_info.components["cpprest"].system_libs.append("bcrypt")
            if self.options.get_safe("pplx_impl") == "winpplx":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_PPLX=1")
            if self.options.get_safe("http_client_impl") == "asio":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_HTTP_CLIENT_ASIO")
            if self.options.get_safe("http_listener_impl") == "asio":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_HTTP_LISTENER_ASIO")
        elif self.settings.os == "Macos":
            self.cpp_info.components["cpprest"].frameworks.extend(["CoreFoundation", "Security"])
        if not self.options.shared:
            self.cpp_info.components["cpprest"].defines.extend(["_NO_ASYNCRTIMP", "_NO_PPLXIMP"])
        # cpprestsdk_zlib_internal
        if self.options.with_compression:
            self.cpp_info.components["cpprestsdk_zlib_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_zlib_internal")
            self.cpp_info.components["cpprestsdk_zlib_internal"].includedirs = []
            self.cpp_info.components["cpprestsdk_zlib_internal"].requires = ["zlib::zlib"]
            self.cpp_info.components["cpprest"].requires.append("cpprestsdk_zlib_internal")
        # cpprestsdk_websocketpp_internal
        if self.options.with_websockets:
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_websocketpp_internal")
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].includedirs = []
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].requires = ["websocketpp::websocketpp"]
            self.cpp_info.components["cpprest"].requires.append("cpprestsdk_websocketpp_internal")
