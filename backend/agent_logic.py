import google.generativeai as genai
import json

class AgentBrain:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')

    def plan_refactoring(self, skeletons, instruction):
        """
        Returns a list of file paths that are relevant to the instruction.
        """
        # Map inputs to a prompt context
        context_str = "\n".join([f"--- {s.file_path} ---\n{s.content_head}\n" for s in skeletons])
        
        prompt = f"""
        Analyze the following file skeletons (first 50 lines).
        User Instruction: "{instruction}"
        
        Return a JSON object with a single key 'relevant_files' containing a list of strings 
        of the file paths that need to be modified or read in depth.
        """
        
        response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)['relevant_files']

    def generate_code(self, full_content, file_path):
        """
        Refactors the specific file.
        """
        system_prompt = self._get_system_prompt()
        prompt = f"""
        File: {file_path}
        Content:
        ```python
        {full_content}
        ```
        
        Refactor this code completely. Output ONLY the code, no markdown fencing needed if possible, 
        but if markdown is used, I will strip it.
        """
        
        response = self.model.generate_content([system_prompt, prompt])
        
        # Basic cleanup of markdown if Gemini adds it
        code = response.text.replace("```python", "").replace("```", "").strip()
        return code

    def _get_system_prompt(self):
        system_prompt = f"""You are a Google Senior Engineer and a world-class Python expert. Your goal is to refactor code to be State-of-the-Art (SOTA).

        Adhere to the following strict guidelines:

        1.  **Type Safety**: You must prioritize Type Hints (Python 3.11+ syntax) for all function arguments and return types. Use `typing.Optional`, `typing.List`, etc., precisely.
        2.  **Algorithmic Efficiency**: Analyze the Big-O notation of the existing code. If an O(n^2) operation can be reduced to O(n) or O(n log n), you must perform that optimization.
        3.  **Documentation & Citations**:
            * Docstrings must follow Google Style.
            * You must cite the research paper, algorithm name, or mathematical source in the docstring if you implement a complex optimization (e.g., "Implements Dijkstra's algorithm optimized with a Fibonacci heap").
        4.  **Preservation**: Retain the original variable naming style (snake_case vs camelCase) unless it is objectively incorrect or violates PEP-8 explicitly. Do not change business logic, only structure and efficiency.
        5.  **Output**: Return the full, runnable file content. Do not output diffs. Do not output markdown conversational text."""
        return system_prompt