# ADR-0003：QML 模块组织 —— qrc 资源 + C++ 注册单例

- **状态**：已定并验证（2026-11-15）
- **相关**：ADR-0004（主题令牌分层）

## 背景

VOLTA 的 QML 有 6 个文件，需要：
1. 文件之间互相引用（Main.qml 用 VideoSlot / Shell / PlaylistPanel / TransportBar）
2. 一个全局 `Theme` 单例，所有颜色/字体只能从它取（主题系统的硬约束）

## 走过的弯路

**方案 A：`qt_add_qml_module`**（Qt 官方推荐）

```cmake
qt_add_qml_module(volta_ui URI VOLTA VERSION 1.0 QML_FILES ...)
```

失败链条：
1. 默认建成 **SHARED 库** → 资源落在 `volta_ui.dll` 里，不在 exe
2. 加 `STATIC` → qmldir 里仍带 `linktarget volta_uiplugin`，指向一个不存在的 plugin dll
3. Qt 判定模块无效 → `No module named "VOLTA" found`
4. 改走 plugin 路线（生成 `volta_uiplugin.dll` 放 exe 旁边）→ 要拷 dll、要配 libraryPaths，仍然脆弱
5. 试 `import VOLTA` 自引用 → 同模块内不需要 import 自己的 URI
6. 试 `contentItem: Item { ... }` → ApplicationWindow 的 contentItem 是**只读**的

**这条路一共试了 6 轮，全是 Qt 模块系统的边角。**

## 决策

**QML 走 `.qrc` 资源，Theme 单例用 C++ 注册。**

```cmake
qt_add_executable(volta
    main.cpp
    volta_qml.qrc        # ← qrc 直接进 exe
)
```

```cpp
// main.cpp
volta::ThemeBridge themeBridge(tokens);
qmlRegisterSingletonInstance("VOLTA", 1, 0, "Theme", &themeBridge);
engine.load(QUrl("qrc:/qml/Main.qml"));
```

QML 侧：
```qml
import QtQuick
import "qrc:/qml"      // ← 同目录互相引用
import VOLTA            // ← C++ 注册的 Theme 单例
```

## 后果

**好处**
- 资源进 exe，无 dll 依赖，无 libraryPaths 配置
- Theme 单例不受模块系统约束，`qmlRegisterSingletonInstance` 是另一条路
- QML 文件之间用 `import "qrc:/qml"` 显式声明，比隐式目录导入更清楚

**代价**
- 失去 Qt 的 QML 类型注册（`QML_ELEMENT` 宏不可用）→ 纯 C++ 类型要手动注册
- 失去 `qmllint` 对模块的自动校验
- `Theme.qml` 里的 `Component`（扫描线/暗角）不能作为单例成员暴露 → 挪到 Main.qml 内联

## 附带的坑（都记在 HANDOFF.md 里）

- `slots` 是 Qt 宏（`#define slots Q_SLOTS`），字段名不能叫 slots
- Repeater delegate 必须声明 `required property var modelData`，否则 `modelData.x` 是 undefined
- GridLayout 用 `rowSpacing`/`columnSpacing`，没有 `spacing`
- Rectangle 没有 `bottomWidth` 之类的单边属性
- ApplicationWindow 不是 Item，`Keys` 挂不上去，要用 `Shortcut`
- Layout 子项的 `minimumWidth` 会撑破容器 → 归零 + `maximumWidth: Infinity`

## 何时推翻

不推翻。这是 Qt 模块系统在没有 plugin 基础设施时的简化路径，代价可控。
