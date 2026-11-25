//!HOOK MAIN
//!BIND HOOKED
//!DESC volta gameboy lcd (4-level green + pixel grid + ghosting)

vec4 hook()
{
    vec2 pos = HOOKED_pos;

    // 像素化：把 UV 量化到低分辨率网格（掌机屏感）
    vec2 grid = vec2(160.0, 144.0);
    vec2 p = floor(pos * grid) / grid + (0.5 / grid);

    vec3 c = HOOKED_tex(p).rgb;

    // 灰度（掌机是单色屏）
    float g = dot(c, vec3(0.299, 0.587, 0.114));

    // 四阶绿（DMG 经典配色）
    vec3 dark  = vec3(0.06, 0.22, 0.06);
    vec3 mdark = vec3(0.19, 0.47, 0.16);
    vec3 mlight= vec3(0.45, 0.70, 0.30);
    vec3 light = vec3(0.68, 0.88, 0.44);
    vec3 col;
    if (g < 0.25)      col = dark;
    else if (g < 0.5)  col = mdark;
    else if (g < 0.75) col = mlight;
    else               col = light;

    // LCD 像素栅格：横竖细暗线
    vec2 cell = fract(pos * grid);
    float mask = 1.0;
    if (cell.x > 0.92 || cell.y > 0.92) mask = 0.86;
    col *= mask;

    // 残影（LCD 响应慢）：和偏移一点的画面混一点
    vec3 ghost = HOOKED_tex(p + vec2(0.006, 0.0)).rgb;
    float gg = dot(ghost, vec3(0.299, 0.587, 0.114));
    col = mix(col, col * (0.8 + 0.4 * gg), 0.25);

    return vec4(col, 1.0);
}
