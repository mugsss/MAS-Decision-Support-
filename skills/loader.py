"""
Skills loader — reads skills.yaml and builds skill chains as LangChain tools.
"""

from pathlib import Path

import yaml
from langchain_core.tools import tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseChatModel


class SkillsLoader:
    def __init__(self, skills_path: str = "skills.yaml"):
        self.skills_path = Path(skills_path)
        self.skills_config: dict = {}

    def load(self) -> dict:
        with open(self.skills_path) as f:
            self.skills_config = yaml.safe_load(f).get("skills", {})
        return self.skills_config

    def build_skill_tools(
        self,
        llm: BaseChatModel,
        available_tools: dict[str, StructuredTool],
    ) -> list[StructuredTool]:
        skill_tools = []
        for skill_name, config in self.skills_config.items():
            skill_tool = self._build_skill(skill_name, config, llm, available_tools)
            if skill_tool:
                skill_tools.append(skill_tool)
        return skill_tools

    def _build_skill(
        self,
        name: str,
        config: dict,
        llm: BaseChatModel,
        available_tools: dict[str, StructuredTool],
    ) -> StructuredTool | None:
        description = config.get("description", name)
        prompt_template = config.get("prompt_template", "")
        tool_names = config.get("tools", [])

        skill_tools = [available_tools[t] for t in tool_names if t in available_tools]

        import re
        template_vars = re.findall(r"\{(\w+)\}", prompt_template)

        def _make_skill_fn(
            _name: str, _desc: str, _template: str, _tools: list, _llm: BaseChatModel, _vars: list
        ):
            def skill_fn(**kwargs) -> str:
                filled = _template
                for var in _vars:
                    filled = filled.replace(f"{{{var}}}", kwargs.get(var, f"<{var}>"))

                results = []
                for t in _tools:
                    try:
                        result = t.invoke(filled)
                        results.append(f"[{t.name}]: {result}")
                    except Exception as e:
                        results.append(f"[{t.name}]: Error — {e}")

                combined_context = "\n\n".join(results)

                synthesis_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an automotive integration expert. Synthesize the following data into a clear, actionable response."),
                    ("human", f"Task: {filled}\n\nData collected:\n{combined_context}\n\nProvide a structured response."),
                ])
                chain = synthesis_prompt | _llm | StrOutputParser()
                return chain.invoke({})

            skill_fn.__name__ = _name
            skill_fn.__doc__ = _desc
            return skill_fn

        fn = _make_skill_fn(name, description, prompt_template, skill_tools, llm, template_vars)

        from pydantic import create_model
        fields = {v: (str, ...) for v in template_vars}
        args_model = create_model(f"{name}_args", **fields) if fields else None

        return StructuredTool(
            name=name,
            description=description,
            func=fn,
            args_schema=args_model,
        )
