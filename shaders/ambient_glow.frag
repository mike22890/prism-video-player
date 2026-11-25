#version 440

layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;

layout(std140, binding=0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float uTime;
    vec4  uTint;
    vec4  uVideoRect;   // xy=视频左上角, zw=视频宽高（归一化）
    float uPad0;
    float uPad1;
} ubuf;

layout(binding=1) uniform sampler2D source;

// Ambilight：取视频「四条边缘带」的颜色，提饱和，糊到外围。
// 关键：采样点贴着边缘(不是中心)，暗像素不整块砍掉(只压一点),否则暗画面完全没光。
vec3 edgeColor(vec2 uv) {
    vec4 vr = ubuf.uVideoRect;
    // 把 uv 投影到视频矩形内：x夹到[左+ε, 右-ε], y夹到[上+ε, 下-ε]
    vec2 inUv = clamp(uv, vr.xy + vec2(0.004), vr.xy + vr.zw - vec2(0.004));
    vec3 acc = vec3(0); float wsum = 0;
    // 5x5 小模糊（纹理已 160x90，够软）
    for (int y=-2; y<=2; ++y) for (int x=-2; x<=2; ++x) {
        vec2 s = clamp(inUv + vec2(float(x),float(y))*0.012, vr.xy+0.002, vr.xy+vr.zw-0.002);
        float w = 1.0/(1.0+float(x*x+y*y)*0.1);
        acc += texture(source, s).rgb * w; wsum += w;
    }
    vec3 col = acc/wsum;
    // 提饱和 1.8x（不过火），亮度整体抬一点
    float lum = dot(col, vec3(0.2126,0.7152,0.0722));
    col = mix(vec3(lum), col, 1.8);
    col = col * 1.25 + vec3(0.02);
    // 极轻主题染色
    col = mix(col, col*(0.7+0.3*ubuf.uTint.rgb), 0.12);
    return min(col, vec3(1));
}

void main(){
    vec2 uv = qt_TexCoord0;
    vec4 vr = ubuf.uVideoRect;
    vec2 d = max(vr.xy - uv, uv - (vr.xy + vr.zw));
    float outside = length(max(d, 0.0));
    if (outside <= 0.0) { fragColor = vec4(0); return; }

    vec3 glow = edgeColor(uv);
    // 扩散：短边 1.4x，能铺满左右空白
    float spread = max(0.12, min(vr.z, vr.w) * 1.4);
    float falloff = exp(-outside / spread);
    float breathe = 0.96 + 0.04*sin(ubuf.uTime*0.7);
    float a = falloff * breathe * 0.9 * ubuf.qt_Opacity;
    fragColor = vec4(glow*a, a);
}
