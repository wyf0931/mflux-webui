import unittest

from mflux_webui.vlm_service import (
    STRUCTURE_FIELDS,
    VlmService,
    build_instruction,
    parse_description,
)


class InstructionTest(unittest.TestCase):
    def test_instruction_lists_every_structure_field_and_focus(self):
        instruction = build_instruction("聚焦人物")
        for field in STRUCTURE_FIELDS:
            self.assertIn(field, instruction)
        self.assertIn("用户关注点：聚焦人物", instruction)
        self.assertIn("只输出一个 JSON 对象", instruction)

    def test_instruction_without_focus_asks_for_balanced_description(self):
        self.assertIn("均衡描述", build_instruction("   "))

    def test_instruction_truncates_long_focus(self):
        instruction = build_instruction("人物" * 200)
        self.assertIn("人物" * 150, instruction)
        self.assertNotIn("人物" * 151, instruction)


class ParseDescriptionTest(unittest.TestCase):
    def test_parses_fenced_json_and_orders_dimensions(self):
        text = """```json
        {"prompt": "A woman sits by the window, soft light.",
         "structure": {"镜头与参数": "50mm f/2.8", "构图与布局": "居中构图", "光线与曝光": "柔和侧光"}}
        ```"""
        result = parse_description(text)
        self.assertEqual(result["prompt"], "A woman sits by the window, soft light.")
        self.assertEqual([row["label"] for row in result["structure"]], ["构图与布局", "光线与曝光", "镜头与参数"])

    def test_accepts_list_structure_and_keeps_extra_dimensions_last(self):
        text = '{"prompt": "p", "structure": [{"label": "自定义维度", "value": "v"}, {"name": "主体与动作", "detail": "站立"}]}'
        result = parse_description(text)
        self.assertEqual([row["label"] for row in result["structure"]], ["主体与动作", "自定义维度"])

    def test_derives_prompt_from_structure_when_prompt_missing(self):
        result = parse_description('{"structure": {"环境与背景": "室内", "色彩与配色": "暖色"}}')
        self.assertEqual(result["prompt"], "环境与背景：室内；色彩与配色：暖色")

    def test_falls_back_to_plain_text_when_json_is_missing(self):
        result = parse_description("A quiet street at dusk.")
        self.assertEqual(result, {"prompt": "A quiet street at dusk.", "structure": []})

    def test_rejects_empty_output(self):
        with self.assertRaises(ValueError):
            parse_description("   ")


class VlmServiceTest(unittest.TestCase):
    def test_missing_cached_model_reports_download_hint(self):
        service = VlmService("example/not-cached")
        service.is_model_cached = lambda: False
        with self.assertRaises(ValueError) as raised:
            service.describe("reference.png")
        self.assertIn("hf download example/not-cached", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
