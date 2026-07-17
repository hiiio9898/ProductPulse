"""翻译服务：英文产品标题 -> 中文搜索关键词。

用于提升 1688 匹配率：1688 是中文平台，英文标题直接搜索匹配率极低。
方案：用 GLM 将英文标题翻译为中文采购关键词（保留规格型号）。
降级：GLM 不可用时回退到规格词表替换。
"""

import re
from typing import Optional

from app.adapters.ai_provider import AIProvider

# 翻译专用：直接用 glm-4-flash（快速、不限流）
_translator_ai = AIProvider(primary="glm-4-flash", fallbacks=["glm-4-flash"])
from app.core.logging import get_logger

logger = get_logger("services.translator")


SPEC_GLOSSARY = {
    "filament": "耗材", "pla": "PLA", "abs": "ABS", "petg": "PETG",
    "tpu": "TPU", "1.75mm": "1.75mm", "3d printer": "3D打印",
    "ink": "墨水", "sublimation": "热转印", "sublimation ink": "热转印墨水",
    "photo paper": "相纸", "glossy": "光面", "matte": "哑光",
    "inkjet": "喷墨", "printer": "打印机", "cartridge": "墨盒",
    "toner": "碳粉", "label": "标签", "sticker": "贴纸",
    "vinyl": "贴膜", "heat transfer": "热转印", "mug": "马克杯",
    "phone case": "手机壳", "cable": "线缆", "charger": "充电器",
    "led": "LED", "strip": "灯带", "bulb": "灯泡",
    "brush": "刷子", "comb": "梳子", "mirror": "镜子",
    "bottle": "瓶子", "container": "容器", "organizer": "收纳",
    "fabric": "面料", "cotton": "棉", "polyester": "涤纶",
    "leather": "皮革", "canvas": "帆布", "mesh": "网眼",
    "stainless steel": "不锈钢", "aluminum": "铝合金", "silicone": "硅胶",
    "wooden": "木质", "bamboo": "竹", "ceramic": "陶瓷",
    "portable": "便携", "foldable": "可折叠", "waterproof": "防水",
    "rechargeable": "可充电", "wireless": "无线", "usb": "USB",
}


def translate_to_chinese(title: str) -> str:
    """英文标题 -> 中文搜索关键词（用于 1688 搜索）。"""
    if not title:
        return ""
    result = _glm_translate(title)
    if result:
        return result
    return _glossary_fallback(title)


def _glm_translate(title: str) -> Optional[str]:
    """用 GLM 翻译为中文采购关键词。"""
    prompt = (
        "You are a sourcing assistant. Translate this English product title into "
        "Chinese keywords suitable for searching on 1688.com (a Chinese wholesale platform). "
        "Rules: 1) Keep spec numbers (e.g. 1.75mm, 200gsm) 2) Remove brand names and marketing words "
        "3) Return ONLY Chinese keywords, no explanation, max 20 characters.\n\n"
        f"Title: {title}"
    )
    try:
        # 翻译直接用 glm-4-flash（快速且不限流，不走 5.2 降级链）
        result = _translator_ai.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
            task_id=None,  # 不记录重试进度（翻译是辅助功能）
        )
        # 如果返回的模型不是 flash，说明走了降级，无所谓
        if result.success and result.content:
            cleaned = result.content.strip().strip("\"").strip("'")
            logger.info("GLM translate OK", original=title[:40], translated=cleaned)
            return cleaned
    except Exception as e:
        logger.warning("GLM translate failed, fallback to glossary", error=str(e))
    return None


def _glossary_fallback(title: str) -> str:
    """词表兜底：英文规格词替换为中文。"""
    lower = title.lower()
    replaced = []
    for en, zh in sorted(SPEC_GLOSSARY.items(), key=lambda x: -len(x[0])):
        if en in lower and zh not in replaced:
            replaced.append(zh)
            lower = lower.replace(en, "")
    specs = re.findall(r"[\d.]+(?:mm|gsm|kg|g|ml|cm|inch|w|v)\b", title.lower())
    result = " ".join(replaced + specs)
    return result.strip() or title[:30]
