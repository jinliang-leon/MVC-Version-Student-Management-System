"""通用字段格式校验器

为什么需要：
    此前 name/class_name 等文本字段只限制长度，纯数字（如 "13131"）也能写入。
    本模块为各 Schema 提供统一的格式校验：

    - validate_person_name   姓名：只允许中文 / 英文字母 / 间隔号（·）/ 空格
    - make_text_validator    通用文本：必须至少含一个中文或字母，禁止 < > 尖括号

约定：
    - 校验只在写入路径生效（Create / Update Schema）；Out 模型不校验，
      保证历史脏数据仍可读取。
    - 抛 ValueError → Pydantic 归为 422，错误文案会出现在响应 message 中。
"""
import re

# 至少包含一个中文或英文字母
_HAS_LETTER_OR_CJK = re.compile(r"[A-Za-z\u4e00-\u9fa5]")

# 中文/全角标点：CJK 标点（U+3000-U+303F，含 【】《》、。）+ 全角符号（U+FF00-U+FFEF）
# 这些在真实业务里很常见：班级名 "Python全栈1班（2026）"、企业名 "深圳沃林（数字）有限公司"、
# 姓名 "张三（大）"，因此必须放行，只拦截真正危险的 < > 与纯符号输入。
_CJK_PUNCT = r"\u3000-\u303f\uff00-\uffef"

# 姓名白名单：中文、英文字母（大小写）、间隔号、空格、中文/全角标点
# 支持 "Tom Lee"、"阿依古丽·买买提"、"张三（大）"
_NAME_ALLOWED = re.compile(rf"^[\u4e00-\u9fa5A-Za-z·\s{_CJK_PUNCT}]+$")

# 危险字符（防 XSS 注入存储）
_DANGEROUS = re.compile(r"[<>]")


def validate_person_name(v: str | None) -> str | None:
    """姓名校验（学生 / 教师）：strip 后不能为空，且只能由中文/字母/间隔号等组成"""
    if v is None:
        return v
    v2 = v.strip()
    if not v2:
        raise ValueError("姓名不能为空白")
    if not _NAME_ALLOWED.fullmatch(v2):
        raise ValueError("姓名只能包含中文、英文字母和间隔号（·），不能是纯数字或特殊符号")
    if _HAS_LETTER_OR_CJK.search(v2) is None:
        raise ValueError("姓名至少需要包含一个中文或英文字母")
    return v2


def make_text_validator(label: str):
    """生成通用文本校验器：strip 后非空、至少含一个中文或字母、无危险字符

    :param label: 字段中文名，用于错误提示，如 "班级名称"、"考试科目"
    """

    def _validate(v: str | None) -> str | None:
        if v is None:
            return v
        v2 = v.strip()
        if not v2:
            raise ValueError(f"{label}不能为空白")
        if not _HAS_LETTER_OR_CJK.search(v2):
            raise ValueError(f"{label}必须包含中文或英文字母，不能是纯数字")
        if _DANGEROUS.search(v2):
            raise ValueError(f"{label}不能包含 < > 等特殊字符")
        return v2

    return _validate
