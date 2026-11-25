//!HOOK MAIN
//!BIND HOOKED
//!DESC volta crt v2 (barrel + bloom + chroma + scanlines + fade)

// 采样时带桶形畸变：越靠边走样越往外推，模拟显像管的球面
vec3 crtAt(vec2 pos)
{
    vec2  d  = (pos - vec2(0.5)) * 2.0;
    float r2 = dot(d, d);
    vec2  p  = pos + d * r2 * 0.030;
    if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0)
        return vec3(0.0);
    return HOOKED_tex(p).rgb;
}

vec4 hook()
{
    vec2 pos = HOOKED_pos;

    // 色差：红蓝各错开一点，像会聚没调好的显像管
    vec3 c  = crtAt(pos);
    vec3 cr = crtAt(pos + vec2(-0.0017, 0.0));
    vec3 cb = crtAt(pos + vec2( 0.0017, 0.0));
    vec3 col = vec3(cr.r, c.g, cb.b);

    // 像素发光：邻域平均当辉光叠上去，亮部会往外晕
    vec3 glow = vec3(0.0);
    glow += crtAt(pos + vec2(-0.0026, 0.0));
    glow += crtAt(pos + vec2( 0.0026, 0.0));
    glow += crtAt(pos + vec2(0.0, -0.0026));
    glow += crtAt(pos + vec2(0.0,  0.0026));
    glow *= 0.25;
    col = col * 0.90 + glow * 0.22;

    // 扫描线：每三行压暗一行，靠 smoothstep 免得出现硬条纹
    float row  = pos.y * HOOKED_size.y;
    float scan = mix(0.66, 1.0, smoothstep(0.0, 0.34, fract(row / 3.0)));

    // 暗角
    vec2  dv  = pos - vec2(0.5);
    float vig = 1.0 - dot(dv, dv) * 0.95;

    // 褪色：抬黑位、压高光，老电视那种发灰的对比
    col = mix(col, col * 0.86 + vec3(0.055, 0.06, 0.055), 0.55);

    return vec4(col * scan * vig, 1.0);
}
