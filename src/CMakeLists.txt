cmake_minimum_required(VERSION 3.24)
project(VOLTA VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Quick QuickControls2 Network Multimedia)

qt_standard_project_setup(REQUIRES 6.5)

# ── libmpv（可选：有就启用路径 B/C，没有也能编译纯 UI 骨架）──
# Windows 的 MinGW 构建产物是 libmpv.dll.a（导入库）+ libmpv-2.dll（运行时）
set(MPV_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../mpv" CACHE PATH "libmpv root")

set(MPV_INCLUDE_DIR "${MPV_ROOT}/include")
set(MPV_IMPORT_LIB "${MPV_ROOT}/libmpv.dll.a")
set(MPV_RUNTIME_DLL "${MPV_ROOT}/libmpv-2.dll")

if(EXISTS "${MPV_INCLUDE_DIR}/mpv/client.h" AND EXISTS "${MPV_IMPORT_LIB}")
    message(STATUS "libmpv FOUND: ${MPV_IMPORT_LIB}")
    add_library(volta_mpv SHARED IMPORTED GLOBAL)
    set_target_properties(volta_mpv PROPERTIES
        IMPORTED_IMPLIB "${MPV_IMPORT_LIB}"
        IMPORTED_LOCATION "${MPV_RUNTIME_DLL}"
        INTERFACE_INCLUDE_DIRECTORIES "${MPV_INCLUDE_DIR}"
    )
    set(VOLTA_HAVE_LIBMPV ON)
else()
    message(WARNING "libmpv NOT found -- building UI-only skeleton")
    set(VOLTA_HAVE_LIBMPV OFF)
endif()

add_library(volta_core STATIC
    core/model.cpp
    core/themebridge.h
    core/themebridge.cpp
    core/appcontroller.cpp
    core/appcontroller.h
    core/windowframe.cpp
    core/windowframe.h
    core/soundbank.cpp
    core/soundbank.h
    core/appassoc.cpp
    core/appassoc.h
)
target_include_directories(volta_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(volta_core PUBLIC Qt6::Core Qt6::Gui Qt6::Multimedia)

# Windows：自绘窗口框架需要 dwmapi（DWM 圆角 + 阴影）
if(WIN32)
    target_link_libraries(volta_core PRIVATE dwmapi shell32)
endif()

# QML 组件作为 qrc 资源编入可执行文件（显式 .qrc 文件，避免 qt_add_resources
# 的 BASE 参数语义差异）。
# 不用 qt_add_qml_module：静态模块的 qmldir 带 linktarget 指向 plugin dll，
# 找不到时 Qt 判定模块无效 → "No module named VOLTA found"。
# Theme 单例由 C++ qmlRegisterSingletonInstance 注册（core/themebridge.h）。
# engine 层：libmpv 集成
add_library(volta_engine STATIC
    engine/mpvitem.cpp
    engine/mpvitem.h
)
target_include_directories(volta_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(volta_engine PUBLIC Qt6::Core Qt6::Gui Qt6::Quick Qt6::OpenGL)
if(VOLTA_HAVE_LIBMPV)
    target_link_libraries(volta_engine PRIVATE volta_mpv)
endif()

# 图标：把 ico 的绝对路径注入 rc（windres 从 build 目录解析相对路径会找不到，
# 导致 exe 用系统默认图标 —— 用户报的「图标没换」就是这么来的）。
set(APP_ICO_PATH "${CMAKE_CURRENT_SOURCE_DIR}/app.ico")
file(TO_CMAKE_PATH "${APP_ICO_PATH}" APP_ICO_PATH)
configure_file(app.rc.in "${CMAKE_CURRENT_BINARY_DIR}/app.rc" @ONLY)

qt_add_executable(volta
    main.cpp
    volta_qml.qrc
    ${CMAKE_CURRENT_BINARY_DIR}/app.rc
)
set_target_properties(volta PROPERTIES OUTPUT_NAME "prism")

target_link_libraries(volta PRIVATE
    volta_core
    volta_engine
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::Gui
    Qt6::Network
    Qt6::Multimedia
)

if(VOLTA_HAVE_LIBMPV)
    target_compile_definitions(volta PRIVATE VOLTA_HAVE_LIBMPV=1)
    target_link_libraries(volta PRIVATE volta_mpv)
    # 运行期 DLL 拷到 bin/
    add_custom_command(TARGET volta POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${MPV_RUNTIME_DLL}" "$<TARGET_FILE_DIR:volta>"
        COMMENT "copying libmpv-2.dll")
else()
    target_compile_definitions(volta PRIVATE VOLTA_HAVE_LIBMPV=0)
endif()

# 不要控制台窗口。不加这一行，双击 exe 会先弹一个黑漆漆的终端
# （console 子系统程序的默认待遇），看着像病毒。
set_target_properties(volta PROPERTIES WIN32_EXECUTABLE TRUE)
