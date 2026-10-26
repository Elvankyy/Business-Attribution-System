import re

from app.analysis.agent.output import AnalysisOutput
from app.analysis.harness.runtime import ToolCallRecord


class AnalysisOutputValidator:
    def validate(
        self, output: AnalysisOutput, tool_results: list[ToolCallRecord]
    ) -> list[str]:
        errors: list[str] = []

        if not output.problem_definition.strip():
            errors.append("问题定义不能为空")
        if not output.key_metrics:
            errors.append("关键指标至少需要 1 项")
        if not output.evidence_list:
            errors.append("证据列表至少需要 1 条")
        if not output.conclusion_text.strip():
            errors.append("归因结论不能为空")

        actions = [
            line.strip(" \t-*•")
            for line in output.next_action_text.splitlines()
            if line.strip(" \t-*•")
        ]
        if len(actions) < 2:
            actions = [
                part.strip()
                for part in re.split(r"[；;]", output.next_action_text)
                if part.strip()
            ]
        if len(actions) < 2:
            errors.append("下一步建议至少需要 2 条")

        successful = [result for result in tool_results if result.success]
        allowed_sources = {result.source_name for result in successful}
        allowed_sources |= {result.tool_name for result in successful}
        for result in successful:
            if isinstance(result.data, dict):
                source_name = result.data.get("source_name")
                if source_name:
                    allowed_sources.add(str(source_name))
                for key in ("rows", "results"):
                    for row in result.data.get(key, []) or []:
                        if isinstance(row, dict) and row.get("source_name"):
                            allowed_sources.add(str(row["source_name"]))

        metric_names = {metric.metric_name for metric in output.key_metrics}
        for index, evidence in enumerate(output.evidence_list, start=1):
            if not evidence.evidence_text.strip():
                errors.append(f"证据 {index} 内容为空")
            if evidence.source_name not in allowed_sources:
                allowed_display = "、".join(sorted(allowed_sources)) or "无"
                errors.append(
                    f"证据 {index} 来源无法追溯到工具结果："
                    f"{evidence.source_name}（可用来源：{allowed_display}）"
                )
            if (
                evidence.related_metric
                and evidence.related_metric not in metric_names
            ):
                errors.append(
                    f"证据 {index} 关联指标不存在：{evidence.related_metric}"
                )

        if not successful and output.evidence_list:
            errors.append("没有成功工具结果，但证据列表非空")

        return errors

    def correction_message(self, errors: list[str]) -> str:
        details = "\n".join(f"- {error}" for error in errors)
        return (
            "上一次输出未通过校验：\n"
            f"{details}\n"
            "请只根据已成功工具结果修正后重新输出。"
        )
