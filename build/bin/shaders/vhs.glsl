//!HOOK MAIN
//!BIND HOOKED
//!DESC volta vhs v2 (tracking band + chroma bleed + grain)

float hash(vec2 p)
{
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec4 hook()
{
    vec2 pos = HOOKED_pos;

    // 横向抖动：行与行错开，像磁带被拉扯
    float wob = sin(pos.y * 220.0) * 0.0012 + sin(pos.y * 37.0) * 0.0009;
    vec2  p   = pos + vec2(wob, 0.0);

    // 色度渗漏：红蓝跑得比绿远
    float r = HOOKED_tex(p + vec2( 0.0022, 0.0)).r;
    float b = HOOKED_tex(p + vec2(-0.0022, 0.0)).b;
    vec4  c = HOOKED_tex(p);

    // 纵向柔化（磁带分辨率低）
    vec3 soft = (HOOKED_tex(p + vec2(0.0, 0.0018)).rgb
               + HOOKED_tex(p - vec2(0.0, 0.0018)).rgb) * 0.25 + c.rgb * 0.5;

    // 追踪噪声带：屏幕上一条慢慢滚的亮带
    float band = smoothstep(0.08, 0.0, abs(fract(pos.y * 1.7) - 0.5));

    // 颗粒
    float n = hash(pos * HOOKED_size) * 0.09;

    vec3 col = vec3(r, soft.g, b) * 0.93 + n + band * 0.05;
    col = mix(col, col * vec3(1.02, 0.99, 1.04), 0.4);   // 偏一点紫，磁带味

    return vec4(col, 1.0);
}
