//!HOOK MAIN
//!BIND HOOKED
//!DESC volta synthwave neon (scanlines + magenta/cyan split + bloom + horizon tint)

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

vec4 hook()
{
    vec2 pos = HOOKED_pos;

    // 轻微桶形：像老 CRT 的弧面
    vec2 d = (pos - 0.5) * 2.0;
    vec2 p = pos + d * dot(d, d) * 0.018;
    if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0)
        return vec4(0.06, 0.02, 0.10, 1.0);   // 紫黑边

    // 霓虹色差：红往品红推，蓝往青推
    vec3 c  = HOOKED_tex(p).rgb;
    vec3 cr = HOOKED_tex(p + vec2( 0.0022, 0.0)).rgb;
    vec3 cb = HOOKED_tex(p - vec2( 0.0022, 0.0)).rgb;
    vec3 col = vec3(mix(c.r, cr.r, 0.55), c.g, mix(c.b, cb.b, 0.55));

    // 辉光：邻域平均叠亮部
    vec3 glow = vec3(0.0);
    glow += HOOKED_tex(p + vec2(-0.004, 0.0)).rgb;
    glow += HOOKED_tex(p + vec2( 0.004, 0.0)).rgb;
    glow += HOOKED_tex(p + vec2(0.0, -0.004)).rgb;
    glow += HOOKED_tex(p + vec2(0.0,  0.004)).rgb;
    glow *= 0.25;
    col += glow * 0.28;

    // 扫描线：每 3 像素一条暗线
    float sl = 0.90 + 0.10 * sin(p.y * HOOKED_size.y * 3.14159 / 1.5);
    col *= sl;

    // 落日色调：下半画面偏暖粉，上半偏冷紫
    float warm = smoothstep(0.35, 0.95, p.y);
    col *= mix(vec3(0.92, 0.85, 1.06), vec3(1.10, 0.90, 1.04), warm);

    // 细颗粒
    col += (hash(p * 913.0) - 0.5) * 0.025;

    return vec4(col, 1.0);
}
