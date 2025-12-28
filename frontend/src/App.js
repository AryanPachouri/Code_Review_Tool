import React, { useState, useEffect, useRef } from 'react';
// --- ADDED ClipboardCopy and Check icons ---
import { AlertCircle, CheckCircle, Info, Loader, X, Code, Zap, Sun, Moon, ClipboardCopy, Check } from 'lucide-react';
import './App.css';

// --- NEW IMPORTS for the code editor ---
import AceEditor from "react-ace";

// Import the mode (language) and themes you want to use
import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-github";       // Light theme
import "ace-builds/src-noconflict/theme-tomorrow_night"; // Dark theme
import "ace-builds/src-noconflict/ext-language_tools"; // For basic autocompletion
// --- END NEW IMPORTS ---

// Use environment variable or default to localhost
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const CodeReviewTool = () => {
  const [code, setCode] = useState(`def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def process_data(items):
    if True:
        results = []
        for item in items:
            results.append(item * 2)
        return results
        print("Unreachable code")
`);
  const [issues, setIssues] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [useLLM, setUseLLM] = useState(false);
  const [error, setError] = useState(null);

  // --- NEW STATE FOR DARK MODE ---
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // --- NEW STATE FOR COPY BUTTON ---
  const [isCopied, setIsCopied] = useState(false);

  // --- NEW EFFECT TO TOGGLE DARK MODE CLASS ---
  useEffect(() => {
    // Get the <html> element
    const root = window.document.documentElement;

    if (isDarkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDarkMode]); // Rerun this effect when isDarkMode changes

  const severityConfig = {
    error: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
    warning: { icon: AlertCircle, color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
    info: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' }
  };

  const analyzeCode = async () => {
    setLoading(true);
    setError(null);
    setSelectedIssue(null);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          use_llm: useLLM,
          focus_areas: ['security', 'performance', 'logic']
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setIssues(data.issues || []);
        setSummary(data.summary);
      } else {
        setError(data.error || 'Analysis failed');
      }
    } catch (err) {
      setError(`Failed to analyze code: ${err.message}`);
      console.error('Analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  // --- NEW FUNCTION TO COPY CODE ---
  const copyToClipboard = () => {
    // Use navigator.clipboard for modern browsers
    // This is more secure and reliable than document.execCommand
    navigator.clipboard.writeText(code).then(() => {
      setIsCopied(true);
      // Reset the icon after 2 seconds
      setTimeout(() => {
        setIsCopied(false);
      }, 2000);
    }, (err) => {
      // Fallback for older browsers or if navigator.clipboard fails
      // (e.g., in non-HTTPS environments)
      try {
        const textArea = document.createElement("textarea");
        textArea.value = code;
        textArea.style.position = "absolute";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        setIsCopied(true);
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      } catch (e) {
         console.error('Failed to copy code: ', err);
      }
    });
  };

  const IssueCard = ({ issue }) => {
    // --- ADDED dark: classes ---
    const config = severityConfig[issue.severity] || severityConfig.info;
    const Icon = config.icon;

    return (
      <div
        className={`border-l-4 ${config.border} ${config.bg} p-4 mb-3 cursor-pointer hover:shadow-md transition-shadow rounded-r dark:bg-gray-800 dark:border-l-blue-500`}
        onClick={() => setSelectedIssue(issue)}
      >
        <div className="flex items-start gap-3">
          <Icon className={`${config.color} mt-1 flex-shrink-0`} size={20} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={`text-xs font-semibold ${config.color} uppercase`}>
                {issue.severity}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">Line {issue.line}</span>
              <span className="text-xs px-2 py-0.5 bg-gray-200 rounded dark:bg-gray-700 dark:text-gray-300">{issue.category}</span>
              {issue.source && (
                <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded dark:bg-purple-900 dark:text-purple-300">
                  {issue.source === 'llm' ? '🤖 AI' : '⚡ Static'}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-800 font-medium mb-1 dark:text-gray-100">{issue.message}</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">{issue.suggestion}</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    // --- ADDED dark: classes ---
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        {/* --- ADDED dark: classes --- */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 dark:bg-gray-800">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <Code className="text-blue-600" size={32} />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Code Review Tool</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Static analysis + AI-powered insights</p>
              </div>
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              
              {/* --- NEW DARK MODE TOGGLE BUTTON --- */}
              <button
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="p-2 rounded-full text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
                title="Toggle dark mode"
              >
                {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
              </button>
            
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={useLLM}
                  onChange={(e) => setUseLLM(e.target.checked)}
                  className="rounded"
                />
                <Zap size={16} className="text-purple-600" />
                Use AI Analysis
              </label>
              <button
                onClick={analyzeCode}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 flex items-center gap-2 transition-colors"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin" size={20} />
                    Analyzing...
                  </>
                ) : (
                  'Analyze Code'
                )}
              </button>
            </div>
          </div>

          {/* Summary */}
          {summary && (
            // --- ADDED dark: classes ---
            <div className="flex gap-4 pt-4 border-t flex-wrap dark:border-gray-700">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded" />
                <span className="text-sm font-medium dark:text-gray-300">{summary.errors} Errors</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded" />
                <span className="text-sm font-medium dark:text-gray-300">{summary.warnings} Warnings</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded" />
                <span className="text-sm font-medium dark:text-gray-300">{summary.info} Info</span>
              </div>
              <div className="ml-auto text-sm text-gray-600 dark:text-gray-400">
                Total: {summary.total_issues} issues found
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Code Editor */}
          {/* --- ADDED dark: classes --- */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden dark:bg-gray-800">
            {/* --- MODIFIED HEADER with Copy Button --- */}
            <div className="flex items-center justify-between bg-gray-800 text-white px-4 py-2 text-sm font-medium dark:bg-gray-700">
              <span>Code Editor</span>
              <button
                onClick={copyToClipboard}
                className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-600 transition-colors"
                title={isCopied ? "Copied!" : "Copy code"}
              >
                {/* Show a checkmark when copied, otherwise the copy icon */}
                {isCopied ? <Check size={16} /> : <ClipboardCopy size={16} />}
              </button>
            </div>
            
            <div className="h-[600px] border-t dark:border-gray-700">
              <AceEditor
                // --- DYNAMICALLY CHANGE THEME ---
                theme={isDarkMode ? "tomorrow_night" : "github"}
                
                mode="python"
                value={code}
                onChange={setCode} // This directly updates the 'code' state
                name="CODE_EDITOR_UNIQUE_ID" // Needs a unique ID
                editorProps={{ $blockScrolling: true }}
                setOptions={{
                  useWorker: false, // Disables a console warning
                  showLineNumbers: true, 
                  tabSize: 4,
                  enableBasicAutocompletion: true,
                  enableLiveAutocompletion: true,
                }}
                fontSize={14}
                showPrintMargin={false} 
                highlightActiveLine={true} 
                style={{ width: '100%', height: '100%' }} // Ensures it fills the div
              />
            </div>
          </div>

          {/* Issues Panel */}
          {/* --- ADDED dark: classes --- */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden dark:bg-gray-800">
            <div className="bg-gray-800 text-white px-4 py-2 text-sm font-medium flex items-center justify-between dark:bg-gray-700">
              <span>Issues & Recommendations</span>
              {issues.length > 0 && (
                <span className="bg-white text-gray-800 px-2 py-0.5 rounded text-xs font-semibold">
                  {issues.length}
                </span>
              )}
            </div>
            <div className="h-[600px] overflow-auto p-4">
              {issues.length === 0 ? (
                // --- ADDED dark: classes ---
                <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-500">
                  <CheckCircle size={48} className="mb-3" />
                  <p className="text-sm text-center">No issues found or waiting for analysis</p>
                  <p className="text-xs text-center mt-2">Paste code and click "Analyze Code"</p>
                </div>
              ) : (
                issues.map((issue, idx) => <IssueCard key={idx} issue={issue} />)
              )}
            </div>
          </div>
        </div>

        {/* Issue Detail Modal */}
        {selectedIssue && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            {/* --- ADDED dark: classes --- */}
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-auto dark:bg-gray-800">
              <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white dark:bg-gray-800 dark:border-gray-700">
                <h3 className="text-lg font-semibold dark:text-gray-100">Issue Details</h3>
                <button
                  onClick={() => setSelectedIssue(null)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <X size={24} />
                </button>
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  <span className={`text-sm font-semibold ${severityConfig[selectedIssue.severity].color} uppercase`}>
                    {selectedIssue.severity}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">Line {selectedIssue.line}</span>
                  <span className="text-sm px-2 py-0.5 bg-gray-200 rounded dark:bg-gray-700 dark:text-gray-300">{selectedIssue.category}</span>
                </div>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">Issue</h4>
                    <p className="text-gray-700 dark:text-gray-300">{selectedIssue.message}</p>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">Suggestion</h4>
                    <p className="text-gray-700 dark:text-gray-300">{selectedIssue.suggestion}</p>
                  </div>
                  {selectedIssue.reasoning && (
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-1 dark:text-gray-100">Reasoning</h4>
                      <p className="text-gray-700 dark:text-gray-300">{selectedIssue.reasoning}</p>
                    </div>
                  )}
                  {/* --- ADDED dark: classes --- */}
                  <div className="bg-gray-50 p-3 rounded dark:bg-gray-900">
                    <h4 className="font-semibold text-gray-900 mb-2 dark:text-gray-100">Code Context</h4>
                    <pre className="text-sm font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {/* This safety check prevents crashes if the line number is bad */}
                      {selectedIssue.line > 0 && selectedIssue.line <= code.split('\n').length ? 
                        code.split('\n')[selectedIssue.line - 1] : 
                        "Code line not available."}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CodeReviewTool;

