#pragma once
// Windows 文件关联注册（HKCU，无管理员，幂等）
namespace volta {
class AppAssociation {
public:
    static void registerIfNeeded();   // 首次运行或版本变更时写一次
};
} // namespace volta
