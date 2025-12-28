from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from typing import Dict, Any, List
import hashlib
import time

# Import our analyzer modules
from analyzers.ast_analyzer import ASTAnalyzer, CodeIssue
from analyzers.llm_integration import LLMCodeReviewer, LLMProvider, ResultMerger

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

# Cache for analysis results
analysis_cache = {}
CACHE_TTL = 3600  # 1 hour

class CodeReviewService:
    """Orchestrates the code review pipeline"""
    
    def __init__(self):
        # Initialize analyzers
        self.ast_analyzer = ASTAnalyzer()
        self.llm_reviewer = None
        
        # Check for LLM API key in environment
        api_key = os.environ.get("LLM_API_KEY")
        provider = os.environ.get("LLM_PROVIDER", "anthropic")
        
        if api_key:
            if provider == "anthropic":
                provider_enum = LLMProvider.ANTHROPIC
            elif provider == "openai":
                provider_enum = LLMProvider.OPENAI
            else:
                provider_enum = LLMProvider.LOCAL
            
            try:
                self.llm_reviewer = LLMCodeReviewer(provider_enum, api_key)
                print(f"✓ LLM reviewer initialized with {provider}")
            except Exception as e:
                print(f"⚠ Failed to initialize LLM reviewer: {e}")
        else:
            print("⚠ No LLM_API_KEY found. Running in AST-only mode.")
    
    def analyze_code(self, code: str, use_llm: bool = True, 
                    focus_areas: List[str] = None) -> Dict[str, Any]:
        """
        Complete code analysis pipeline
        
        Args:
            code: Source code to analyze
            use_llm: Whether to use LLM for advanced analysis
            focus_areas: Specific areas to focus on
        
        Returns:
            Dictionary with analysis results
        """
        start_time = time.time()
        
        # Step 1: Static AST analysis
        ast_issues = []
        try:
            ast_issues_obj = self.ast_analyzer.analyze(code)
            ast_issues = [issue.to_dict() for issue in ast_issues_obj]
            for issue in ast_issues:
                issue['source'] = 'ast'
        except Exception as e:
            print(f"AST analysis error: {e}")
        
        # Step 2: LLM analysis (if enabled and available)
        llm_issues = []
        if use_llm and self.llm_reviewer:
            try:
                llm_issues_obj = self.llm_reviewer.review_code(
                    code, ast_issues, focus_areas
                )
                llm_issues = [
                    {
                        "line": issue.line,
                        "column": 0,
                        "severity": issue.severity,
                        "category": issue.category,
                        "message": issue.message,
                        "suggestion": issue.suggestion,
                        "reasoning": issue.reasoning,
                        "source": "llm"
                    }
                    for issue in llm_issues_obj
                ]
            except Exception as e:
                print(f"LLM analysis failed: {str(e)}")
        
        # Step 3: Merge results
        if ast_issues and llm_issues:
            all_issues = ResultMerger.merge_results(ast_issues, llm_issues)
        else:
            all_issues = ast_issues + llm_issues
        
        # Step 4: Generate summary statistics
        summary = self._generate_summary(all_issues)
        
        # Step 5: Format for frontend
        result = {
            "success": True,
            "analysis_time": round(time.time() - start_time, 2),
            "summary": summary,
            "issues": all_issues,
            "code_lines": len(code.split('\n')),
            "llm_used": use_llm and self.llm_reviewer is not None
        }
        
        return result
    
    def _generate_summary(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from issues"""
        summary = {
            "total_issues": len(issues),
            "errors": sum(1 for i in issues if i["severity"] == "error"),
            "warnings": sum(1 for i in issues if i["severity"] == "warning"),
            "info": sum(1 for i in issues if i["severity"] == "info"),
            "categories": {}
        }
        
        # Count by category
        for issue in issues:
            category = issue.get("category", "general")
            summary["categories"][category] = summary["categories"].get(category, 0) + 1
        
        return summary

# Initialize service
review_service = CodeReviewService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "llm_available": review_service.llm_reviewer is not None,
        "ast_available": review_service.ast_analyzer is not None
    })

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("20 per minute")
def analyze_code():
    """
    Main endpoint for code analysis
    
    Expected JSON body:
    {
        "code": "def foo():\n    pass",
        "use_llm": true,
        "focus_areas": ["security", "performance"]
    }
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'code' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'code' in request body"
            }), 400
        
        code = data['code']
        use_llm = data.get('use_llm', True)
        focus_areas = data.get('focus_areas', None)
        
        # Validate code length
        if len(code) > 50000:  # 50KB limit
            return jsonify({
                "success": False,
                "error": "Code exceeds maximum length of 50,000 characters"
            }), 400
        
        if not code.strip():
            return jsonify({
                "success": False,
                "error": "Code cannot be empty"
            }), 400
        
        # Check cache
        cache_key = hashlib.md5(
            f"{code}:{use_llm}:{focus_areas}".encode()
        ).hexdigest()
        
        if cache_key in analysis_cache:
            cached_result, timestamp = analysis_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                cached_result['from_cache'] = True
                return jsonify(cached_result)
        
        # Perform analysis
        result = review_service.analyze_code(code, use_llm, focus_areas)
        
        # Cache result
        analysis_cache[cache_key] = (result, time.time())
        result['from_cache'] = False
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }), 500

@app.route('/api/analyze/batch', methods=['POST'])
@limiter.limit("5 per minute")
def analyze_batch():
    """
    Batch analysis endpoint for multiple code snippets
    
    Expected JSON body:
    {
        "snippets": [
            {"id": "file1", "code": "..."},
            {"id": "file2", "code": "..."}
        ],
        "use_llm": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'snippets' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'snippets' in request body"
            }), 400
        
        snippets = data['snippets']
        use_llm = data.get('use_llm', True)
        
        if len(snippets) > 10:
            return jsonify({
                "success": False,
                "error": "Maximum 10 snippets per batch request"
            }), 400
        
        results = []
        for snippet in snippets:
            snippet_id = snippet.get('id', 'unknown')
            code = snippet.get('code', '')
            
            try:
                result = review_service.analyze_code(code, use_llm)
                results.append({
                    "id": snippet_id,
                    "success": True,
                    "data": result
                })
            except Exception as e:
                results.append({
                    "id": snippet_id,
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "results": results
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Batch analysis failed: {str(e)}"
        }), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get available issue categories"""
    return jsonify({
        "categories": [
            {"id": "syntax", "name": "Syntax Errors", "color": "#dc2626"},
            {"id": "logic", "name": "Logic Errors", "color": "#ea580c"},
            {"id": "security", "name": "Security", "color": "#c026d3"},
            {"id": "performance", "name": "Performance", "color": "#2563eb"},
            {"id": "style", "name": "Code Style", "color": "#059669"},
            {"id": "best_practice", "name": "Best Practices", "color": "#0891b2"},
            {"id": "edge_case", "name": "Edge Cases", "color": "#7c3aed"},
            {"id": "unused", "name": "Unused Code", "color": "#64748b"}
        ]
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate limit error handler"""
    return jsonify({
        "success": False,
        "error": "Rate limit exceeded. Please try again later."
    }), 429

@app.errorhandler(404)
def not_found(e):
    """404 handler"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def server_error(e):
    """500 handler"""
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("Code Review Tool Backend Server")
    print("=" * 50)
    print(f"AST Analyzer: {'✓ Ready' if review_service.ast_analyzer else '✗ Failed'}")
    print(f"LLM Reviewer: {'✓ Ready' if review_service.llm_reviewer else '✗ Not configured'}")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("=" * 50)
    
    # For development only
    app.run(debug=True, host='0.0.0.0', port=5000)