//!HOOK MAIN
//!BIND HOOKED
//!DESC volta nes pixelate (chunky pixels + slight color crunch)

vec4 hook()
{
    vec2 pos = HOOKED_pos;
    // 粗像素块：8bit 机分辨率很低
    vec2 grid = vec2(256.0, 224.0);
    vec2 p = floor(pos * grid) / grid + (0.5 / grid);
    vec3 c = HOOKED_tex(p).rgb;
    // 色彩量化：每通道压到 6 级，像有限调色板
    c = floor(c * 6.0 + 0.5) / 6.0;
    // 轻微提饱和
    float g = dot(c, vec3(0.299, 0.587, 0.114));
    c = mix(vec3(g), c, 1.25);
    return vec4(clamp(c, 0.0, 1.0), 1.0);
}
