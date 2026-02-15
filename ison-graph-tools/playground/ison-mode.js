/**
 * CodeMirror mode for ISON (Implicit Schema Object Notation)
 */

(function(mod) {
    if (typeof exports == "object" && typeof module == "object")
        mod(require("codemirror"));
    else if (typeof define == "function" && define.amd)
        define(["codemirror"], mod);
    else
        mod(CodeMirror);
})(function(CodeMirror) {
    "use strict";

    CodeMirror.defineMode("ison", function() {
        return {
            startState: function() {
                return {
                    inSection: false,
                    isHeader: false
                };
            },

            token: function(stream, state) {
                // Skip whitespace
                if (stream.eatSpace()) return null;

                // Comments
                if (stream.match(/^#.*/)) {
                    return "comment";
                }

                // Graph header
                if (stream.sol() && stream.match(/^graph\s+\w+/)) {
                    return "keyword";
                }

                // Directed/undirected
                if (stream.sol() && stream.match(/^(directed|undirected)$/)) {
                    return "keyword";
                }

                // Node section header
                if (stream.sol() && stream.match(/^nodes\.[a-zA-Z_][a-zA-Z0-9_]*/)) {
                    state.inSection = 'nodes';
                    state.isHeader = true;
                    return "def";
                }

                // Edge section header
                if (stream.sol() && stream.match(/^edges\.[A-Z_][A-Z0-9_]*/)) {
                    state.inSection = 'edges';
                    state.isHeader = true;
                    return "def";
                }

                // Schema header
                if (stream.sol() && stream.match(/^schema\.[a-zA-Z_][a-zA-Z0-9_]*/)) {
                    return "type";
                }

                // Node reference :type:id
                if (stream.match(/^:[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_-]+/)) {
                    return "variable-2";
                }

                // Strings
                if (stream.match(/^"(?:[^"\\]|\\.)*"/)) {
                    return "string";
                }
                if (stream.match(/^'(?:[^'\\]|\\.)*'/)) {
                    return "string";
                }

                // Booleans
                if (stream.match(/^(true|false|True|False|TRUE|FALSE)\b/)) {
                    return "atom";
                }

                // Null
                if (stream.match(/^(null|nil|none|None|NULL)\b/)) {
                    return "atom";
                }

                // Numbers (float)
                if (stream.match(/^-?\d+\.\d+([eE][+-]?\d+)?/)) {
                    return "number";
                }

                // Numbers (integer)
                if (stream.match(/^-?\d+\b/)) {
                    return "number";
                }

                // Constraint keywords
                if (stream.match(/^(required|optional|unique|min|max|pattern|enum)\b/)) {
                    return "builtin";
                }

                // Column headers (identifiers at start of line after section)
                if (state.isHeader && stream.sol()) {
                    state.isHeader = false;
                }

                // Generic word/identifier
                if (stream.match(/^[a-zA-Z_][a-zA-Z0-9_-]*/)) {
                    if (state.isHeader) {
                        return "attribute";
                    }
                    return "variable";
                }

                // Operators
                if (stream.match(/^[=<>!]+/)) {
                    return "operator";
                }

                // Skip unknown character
                stream.next();
                return null;
            }
        };
    });

    CodeMirror.defineMIME("text/x-ison", "ison");
    CodeMirror.defineMIME("text/ison", "ison");
});
