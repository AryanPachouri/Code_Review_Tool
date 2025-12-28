import ast
import sys
from typing import List, Dict, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class CodeIssue:
    line: int
    column: int
    severity: IssueSeverity
    category: str
    message: str
    suggestion: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['severity'] = self.severity.value
        return result

class ASTAnalyzer(ast.NodeVisitor):
    """Static code analyzer using Python's AST module"""
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.defined_vars: Set[str] = set()
        self.used_vars: Set[str] = set()
        self.imported_names: Set[str] = set()
        self.used_imports: Set[str] = set()
        self.function_returns: Dict[str, List[ast.AST]] = {}
        self.current_function: str = None
        
    def analyze(self, code: str) -> List[CodeIssue]:
        """Main entry point for code analysis"""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            self._check_unused_imports()
            self._check_unused_variables()
            return sorted(self.issues, key=lambda x: (x.line, x.column))
        except SyntaxError as e:
            return [CodeIssue(
                line=e.lineno or 0,
                column=e.offset or 0,
                severity=IssueSeverity.ERROR,
                category="syntax",
                message=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error before proceeding"
            )]
        except Exception as e:
            return [CodeIssue(
                line=0,
                column=0,
                severity=IssueSeverity.ERROR,
                category="parsing",
                message=f"Failed to parse code: {str(e)}",
                suggestion="Ensure the code is valid Python"
            )]
    
    def visit_Import(self, node: ast.Import):
        """Track imports"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Track variable usage and definitions"""
        if isinstance(node.ctx, ast.Store):
            self.defined_vars.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.used_vars.add(node.id)
            if node.id in self.imported_names:
                self.used_imports.add(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions"""
        self.current_function = node.name
        self.function_returns[node.name] = []
        
        # Check for unreachable code after return
        self._check_unreachable_code(node.body)
        
        # Store function name as defined
        self.defined_vars.add(node.name)
        
        self.generic_visit(node)
        
        # Check return type consistency
        self._check_return_consistency(node)
        self.current_function = None
    
    def visit_Return(self, node: ast.Return):
        """Track return statements"""
        if self.current_function:
            self.function_returns[self.current_function].append(node)
        self.generic_visit(node)
    
    def visit_If(self, node: ast.If):
        """Check for suspicious if conditions"""
        # Check for constant conditions
        if isinstance(node.test, ast.Constant):
            self.issues.append(CodeIssue(
                line=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category="logic",
                message=f"Condition is always {node.test.value}",
                suggestion="Remove the if statement or fix the condition"
            ))
        
        # Check for comparison with True/False
        if isinstance(node.test, ast.Compare):
            for comparator in node.test.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, bool):
                    self.issues.append(CodeIssue(
                        line=node.lineno,
                        column=node.col_offset,
                        severity=IssueSeverity.WARNING,
                        category="style",
                        message="Avoid comparing with True/False explicitly",
                        suggestion="Use 'if var:' instead of 'if var == True:'"
                    ))
        
        self.generic_visit(node)
    
    def visit_While(self, node: ast.While):
        """Check for infinite loops"""
        if isinstance(node.test, ast.Constant) and node.test.value == True:
            # Check if there's a break statement
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self.issues.append(CodeIssue(
                    line=node.lineno,
                    column=node.col_offset,
                    severity=IssueSeverity.WARNING,
                    category="logic",
                    message="Potential infinite loop without break statement",
                    suggestion="Add a break condition or use a different loop structure"
                ))
        self.generic_visit(node)
    
    def visit_Except(self, node: ast.ExceptHandler):
        """Check for bare except clauses"""
        if node.type is None:
            self.issues.append(CodeIssue(
                line=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category="best_practice",
                message="Bare except clause catches all exceptions",
                suggestion="Specify exception types or use 'except Exception:'"
            ))
        self.generic_visit(node)
    
    def _check_unreachable_code(self, body: List[ast.AST]):
        """Detect code after return/raise statements"""
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise)):
                if i < len(body) - 1:
                    next_stmt = body[i + 1]
                    self.issues.append(CodeIssue(
                        line=next_stmt.lineno,
                        column=next_stmt.col_offset,
                        severity=IssueSeverity.ERROR,
                        category="logic",
                        message="Unreachable code after return/raise",
                        suggestion="Remove or move this code before the return/raise"
                    ))
    
    def _check_return_consistency(self, node: ast.FunctionDef):
        """Check if function returns are consistent"""
        returns = self.function_returns.get(node.name, [])
        if not returns:
            return
        
        has_value = [r.value is not None for r in returns]
        if any(has_value) and not all(has_value):
            self.issues.append(CodeIssue(
                line=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category="logic",
                message=f"Function '{node.name}' has inconsistent return statements",
                suggestion="Ensure all code paths return a value or all return None"
            ))
    
    def _check_unused_imports(self):
        """Identify imports that are never used"""
        unused = self.imported_names - self.used_imports
        for name in unused:
            self.issues.append(CodeIssue(
                line=1,  # We don't track exact line for imports in this simple version
                column=0,
                severity=IssueSeverity.INFO,
                category="unused",
                message=f"Imported '{name}' is never used",
                suggestion=f"Remove the import or use '{name}' in your code"
            ))
    
    def _check_unused_variables(self):
        """Identify variables that are defined but never used"""
        # Exclude special names and built-ins
        builtins = set(dir(__builtins__))
        unused = (self.defined_vars - self.used_vars) - builtins
        # Filter out common patterns like _ or variables starting with _
        unused = {v for v in unused if not v.startswith('_')}
        
        for name in unused:
            self.issues.append(CodeIssue(
                line=0,
                column=0,
                severity=IssueSeverity.INFO,
                category="unused",
                message=f"Variable '{name}' is defined but never used",
                suggestion=f"Remove '{name}' or use it in your code"
            ))

# Example usage
if __name__ == "__main__":
    sample_code = """
import os
import sys

def calculate(x):
    if True:
        result = x * 2
        return result
        print("This won't execute")
    
def process():
    return 5
    unused_var = 10

def inconsistent_return(flag):
    if flag:
        return True
    # Missing return for else case
"""
    
    analyzer = ASTAnalyzer()
    issues = analyzer.analyze(sample_code)
    
    for issue in issues:
        print(f"[{issue.severity.value.upper()}] Line {issue.line}: {issue.message}")
        print(f"  Suggestion: {issue.suggestion}\n")