import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import anthropic
import openai
from enum import Enum

class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"

@dataclass
class LLMIssue:
    """Issue detected by LLM analysis"""
    line: int
    severity: str
    category: str
    message: str
    suggestion: str
    reasoning: str = ""

class LLMCodeReviewer:
    """Integrates with LLM APIs for advanced code review"""
    
    def __init__(self, provider: LLMProvider, api_key: str, model: str = None):
        self.provider = provider
        self.api_key = api_key
        
        if provider == LLMProvider.ANTHROPIC:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model or "claude-sonnet-4-20250514"
        elif provider == LLMProvider.OPENAI:
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model or "gpt-4"
        else:
            # For local models, you'd use something like Ollama
            self.client = None
            self.model = model or "codellama"
    
    def review_code(self, code: str, ast_issues: List[Dict[str, Any]], 
                    focus_areas: Optional[List[str]] = None) -> List[LLMIssue]:
        """
        Send code to LLM for review with context from AST analysis
        
        Args:
            code: The source code to review
            ast_issues: Issues found by static analysis
            focus_areas: Specific areas to focus on (e.g., ['security', 'performance'])
        
        Returns:
            List of LLMIssue objects
        """
        prompt = self._build_prompt(code, ast_issues, focus_areas)
        
        try:
            if self.provider == LLMProvider.ANTHROPIC:
                response = self._call_anthropic(prompt)
            elif self.provider == LLMProvider.OPENAI:
                response = self._call_openai(prompt)
            else:
                response = self._call_local(prompt)
            
            return self._parse_llm_response(response, code)
        
        except Exception as e:
            print(f"LLM API error: {str(e)}")
            return []
    
    def _build_prompt(self, code: str, ast_issues: List[Dict[str, Any]], 
                     focus_areas: Optional[List[str]] = None) -> str:
        """Construct the prompt for LLM review"""
        
        # Format AST issues for context
        ast_context = ""
        if ast_issues:
            ast_context = "Static analysis found these issues:\n"
            for issue in ast_issues[:10]:  # Limit to avoid token overflow
                ast_context += f"- Line {issue['line']}: {issue['message']}\n"
        
        focus_text = ""
        if focus_areas:
            focus_text = f"\nPay special attention to: {', '.join(focus_areas)}"
        
        prompt = f"""You are an expert code reviewer. Analyze the following Python code for:

1. **Logic errors**: Bugs, incorrect algorithms, edge cases not handled
2. **Bad practices**: Anti-patterns, code smells, maintainability issues
3. **Security vulnerabilities**: SQL injection, XSS, insecure data handling
4. **Performance issues**: Inefficient algorithms, unnecessary operations
5. **Missing edge cases**: Null checks, boundary conditions, error handling

{ast_context}

{focus_text}

Please provide feedback in the following JSON format:
{{
  "issues": [
    {{
      "line": <line_number>,
      "severity": "error|warning|info",
      "category": "logic|security|performance|style|edge_case",
      "message": "Brief description of the issue",
      "suggestion": "Specific recommendation to fix",
      "reasoning": "Why this is an issue"
    }}
  ]
}}

Code to review:

```python
{code}
```

Provide only valid JSON in your response, no additional text."""

        return prompt
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic's Claude API"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI's API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert code reviewer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    
    def _call_local(self, prompt: str) -> str:
        """Call local LLM (e.g., via Ollama)"""
        # Example with Ollama API
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json().get("response", "")
    
    def _parse_llm_response(self, response: str, code: str) -> List[LLMIssue]:
        """Parse LLM response into structured issues"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            
            # Try to parse as JSON
            data = json.loads(response)
            issues = []
            
            for issue_data in data.get("issues", []):
                # Validate line number
                code_lines = code.split('\n')
                line = issue_data.get("line", 0)
                if line < 1 or line > len(code_lines):
                    line = 1
                
                issues.append(LLMIssue(
                    line=line,
                    severity=issue_data.get("severity", "info"),
                    category=issue_data.get("category", "general"),
                    message=issue_data.get("message", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    reasoning=issue_data.get("reasoning", "")
                ))
            
            return issues
        
        except json.JSONDecodeError:
            # Fallback: try to extract issues from unstructured text
            return self._extract_issues_from_text(response)
    
    def _extract_issues_from_text(self, text: str) -> List[LLMIssue]:
        """Fallback parser for unstructured LLM responses"""
        issues = []
        
        # Try to find line references like "Line 5:" or "line 10:"
        line_pattern = r'[Ll]ine\s+(\d+)[:.\s]+(.*?)(?=\n[Ll]ine|\n\n|$)'
        matches = re.finditer(line_pattern, text, re.DOTALL)
        
        for match in matches:
            line_num = int(match.group(1))
            content = match.group(2).strip()
            
            # Infer severity from keywords
            severity = "info"
            if any(word in content.lower() for word in ["error", "bug", "critical", "broken"]):
                severity = "error"
            elif any(word in content.lower() for word in ["warning", "potential", "should"]):
                severity = "warning"
            
            issues.append(LLMIssue(
                line=line_num,
                severity=severity,
                category="general",
                message=content[:200],  # Truncate long messages
                suggestion="See LLM feedback for details",
                reasoning=""
            ))
        
        return issues

class ResultMerger:
    """Merges AST and LLM analysis results"""
    
    @staticmethod
    def merge_results(ast_issues: List[Dict[str, Any]], 
                     llm_issues: List[LLMIssue]) -> List[Dict[str, Any]]:
        """
        Combine and deduplicate issues from both analyzers
        
        Returns:
            Merged list sorted by line number and severity
        """
        # Convert LLM issues to dict format
        all_issues = list(ast_issues)
        
        for llm_issue in llm_issues:
            issue_dict = {
                "line": llm_issue.line,
                "column": 0,
                "severity": llm_issue.severity,
                "category": llm_issue.category,
                "message": llm_issue.message,
                "suggestion": llm_issue.suggestion,
                "source": "llm",
                "reasoning": llm_issue.reasoning
            }
            
            # Check for duplicates (same line, similar message)
            is_duplicate = False
            for existing in all_issues:
                if (existing["line"] == issue_dict["line"] and 
                    ResultMerger._similarity(existing["message"], issue_dict["message"]) > 0.7):
                    # Merge information from both sources
                    existing["suggestion"] += f" (LLM: {issue_dict['suggestion']})"
                    existing["source"] = "ast+llm"
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                all_issues.append(issue_dict)
        
        # Sort by severity (error > warning > info) then by line number
        severity_order = {"error": 0, "warning": 1, "info": 2}
        return sorted(all_issues, 
                     key=lambda x: (severity_order.get(x["severity"], 3), x["line"]))
    
    @staticmethod
    def _similarity(text1: str, text2: str) -> float:
        """Simple similarity check between two strings"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

# Example usage
if __name__ == "__main__":
    # Example with mock data (requires actual API key)
    sample_code = """
def divide(a, b):
    return a / b

def process_data(items):
    results = []
    for item in items:
        results.append(item * 2)
    return results
"""
    
    ast_issues = [
        {
            "line": 2,
            "column": 0,
            "severity": "warning",
            "category": "logic",
            "message": "No check for division by zero",
            "suggestion": "Add validation for b != 0"
        }
    ]
    
    # Mock LLM reviewer (would need actual API key)
    # reviewer = LLMCodeReviewer(LLMProvider.ANTHROPIC, "your-api-key")
    # llm_issues = reviewer.review_code(sample_code, ast_issues)
    
    # Mock LLM issues for demonstration
    llm_issues = [
        LLMIssue(
            line=2,
            severity="error",
            category="edge_case",
            message="Missing zero division check",
            suggestion="Add 'if b == 0: raise ValueError' before division",
            reasoning="Division by zero will crash the program"
        ),
        LLMIssue(
            line=5,
            severity="warning",
            category="performance",
            message="List comprehension would be more efficient",
            suggestion="Use 'return [item * 2 for item in items]'",
            reasoning="List comprehension is faster than append in loop"
        )
    ]
    
    # Merge results
    merged = ResultMerger.merge_results(ast_issues, llm_issues)
    
    print("Merged Results:")
    for issue in merged:
        print(f"\n[{issue['severity'].upper()}] Line {issue['line']}: {issue['message']}")
        print(f"  Suggestion: {issue['suggestion']}")
        if "reasoning" in issue:
            print(f"  Reasoning: {issue['reasoning']}")