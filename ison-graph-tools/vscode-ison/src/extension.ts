import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('ISON Language Support is now active');

    // Register commands
    const convertFromJson = vscode.commands.registerCommand('ison.convertFromJson', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const text = editor.document.getText();
        try {
            const json = JSON.parse(text);
            const ison = jsonToIson(json);

            // Create new document with ISON content
            const doc = await vscode.workspace.openTextDocument({
                content: ison,
                language: 'ison'
            });
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage('Converted JSON to ISON');
        } catch (e) {
            vscode.window.showErrorMessage('Failed to parse JSON: ' + e);
        }
    });

    const convertToJson = vscode.commands.registerCommand('ison.convertToJson', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const text = editor.document.getText();
        try {
            const json = isonToJson(text);

            // Create new document with JSON content
            const doc = await vscode.workspace.openTextDocument({
                content: JSON.stringify(json, null, 2),
                language: 'json'
            });
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage('Converted ISON to JSON');
        } catch (e) {
            vscode.window.showErrorMessage('Failed to parse ISON: ' + e);
        }
    });

    const formatDocument = vscode.commands.registerCommand('ison.formatDocument', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const text = editor.document.getText();
        const formatted = formatIson(text);

        editor.edit(editBuilder => {
            const fullRange = new vscode.Range(
                editor.document.positionAt(0),
                editor.document.positionAt(text.length)
            );
            editBuilder.replace(fullRange, formatted);
        });
    });

    const validateDocument = vscode.commands.registerCommand('ison.validateDocument', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const text = editor.document.getText();
        const errors = validateIson(text);

        if (errors.length === 0) {
            vscode.window.showInformationMessage('ISON document is valid');
        } else {
            const diagnostics: vscode.Diagnostic[] = errors.map(err => {
                const range = new vscode.Range(err.line, 0, err.line, 100);
                return new vscode.Diagnostic(range, err.message, vscode.DiagnosticSeverity.Error);
            });

            const diagnosticCollection = vscode.languages.createDiagnosticCollection('ison');
            diagnosticCollection.set(editor.document.uri, diagnostics);

            vscode.window.showErrorMessage(`Found ${errors.length} error(s) in ISON document`);
        }
    });

    // Register document formatter
    const formatter = vscode.languages.registerDocumentFormattingEditProvider('ison', {
        provideDocumentFormattingEdits(document: vscode.TextDocument): vscode.TextEdit[] {
            const text = document.getText();
            const formatted = formatIson(text);
            const fullRange = new vscode.Range(
                document.positionAt(0),
                document.positionAt(text.length)
            );
            return [vscode.TextEdit.replace(fullRange, formatted)];
        }
    });

    // Register hover provider
    const hoverProvider = vscode.languages.registerHoverProvider('ison', {
        provideHover(document, position) {
            const range = document.getWordRangeAtPosition(position, /:[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_-]+/);
            if (range) {
                const word = document.getText(range);
                const parts = word.slice(1).split(':');
                return new vscode.Hover([
                    `**Node Reference**`,
                    `- Type: \`${parts[0]}\``,
                    `- ID: \`${parts[1]}\``
                ].join('\n'));
            }
            return null;
        }
    });

    context.subscriptions.push(
        convertFromJson,
        convertToJson,
        formatDocument,
        validateDocument,
        formatter,
        hoverProvider
    );
}

export function deactivate() {}

// Helper functions

interface GraphJson {
    name?: string;
    directed?: boolean;
    nodes: any[];
    edges: any[];
}

function jsonToIson(json: GraphJson): string {
    const lines: string[] = [];

    // Graph header
    if (json.name) {
        lines.push(`graph ${json.name}`);
        lines.push(json.directed !== false ? 'directed' : 'undirected');
        lines.push('');
    }

    // Group nodes by type
    const nodesByType: Record<string, any[]> = {};
    for (const node of json.nodes || []) {
        const type = node.type || 'entity';
        if (!nodesByType[type]) {
            nodesByType[type] = [];
        }
        nodesByType[type].push(node);
    }

    // Write node sections
    for (const [type, nodes] of Object.entries(nodesByType)) {
        lines.push(`nodes.${type}`);

        // Collect all property keys
        const keys = new Set<string>();
        keys.add('id');
        for (const node of nodes) {
            for (const key of Object.keys(node)) {
                if (key !== 'type' && key !== 'id') {
                    keys.add(key);
                }
            }
        }

        const keyList = Array.from(keys);
        lines.push(keyList.join(' '));

        // Write node data
        for (const node of nodes) {
            const values = keyList.map(k => {
                if (k === 'id') return node.id;
                const v = node[k];
                if (v === undefined || v === null) return '';
                if (typeof v === 'string' && v.includes(' ')) return `"${v}"`;
                return String(v);
            });
            lines.push(values.join(' '));
        }
        lines.push('');
    }

    // Group edges by type
    const edgesByType: Record<string, any[]> = {};
    for (const edge of json.edges || []) {
        const type = edge.rel_type || edge.type || 'RELATED_TO';
        if (!edgesByType[type]) {
            edgesByType[type] = [];
        }
        edgesByType[type].push(edge);
    }

    // Write edge sections
    for (const [type, edges] of Object.entries(edgesByType)) {
        lines.push(`edges.${type}`);

        // Collect property keys
        const keys = new Set<string>();
        keys.add('source');
        keys.add('target');
        for (const edge of edges) {
            for (const key of Object.keys(edge.properties || {})) {
                keys.add(key);
            }
        }

        const keyList = Array.from(keys);
        lines.push(keyList.join(' '));

        // Write edge data
        for (const edge of edges) {
            const source = edge.source;
            const target = edge.target;
            const sourceRef = `:${source.type}:${source.id}`;
            const targetRef = `:${target.type}:${target.id}`;

            const values = keyList.map(k => {
                if (k === 'source') return sourceRef;
                if (k === 'target') return targetRef;
                const v = edge.properties?.[k];
                if (v === undefined || v === null) return '';
                return String(v);
            });
            lines.push(values.join(' '));
        }
        lines.push('');
    }

    return lines.join('\n');
}

function isonToJson(ison: string): GraphJson {
    const result: GraphJson = {
        nodes: [],
        edges: []
    };

    const lines = ison.split('\n');
    let currentSection = '';
    let currentType = '';
    let headers: string[] = [];

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;

        if (trimmed.startsWith('graph ')) {
            result.name = trimmed.slice(6);
            continue;
        }

        if (trimmed === 'directed' || trimmed === 'undirected') {
            result.directed = trimmed === 'directed';
            continue;
        }

        if (trimmed.startsWith('nodes.')) {
            currentSection = 'nodes';
            currentType = trimmed.slice(6);
            headers = [];
            continue;
        }

        if (trimmed.startsWith('edges.')) {
            currentSection = 'edges';
            currentType = trimmed.slice(6);
            headers = [];
            continue;
        }

        // Parse headers or data
        const parts = parseIsonLine(trimmed);

        if (headers.length === 0) {
            headers = parts;
            continue;
        }

        // Parse data row
        if (currentSection === 'nodes') {
            const node: any = { type: currentType };
            for (let i = 0; i < headers.length && i < parts.length; i++) {
                node[headers[i]] = parseValue(parts[i]);
            }
            result.nodes.push(node);
        } else if (currentSection === 'edges') {
            const edge: any = {
                rel_type: currentType,
                properties: {}
            };
            for (let i = 0; i < headers.length && i < parts.length; i++) {
                const header = headers[i];
                const value = parts[i];

                if (header === 'source' || header === 'target') {
                    const ref = parseNodeRef(value);
                    edge[header] = ref;
                } else {
                    edge.properties[header] = parseValue(value);
                }
            }
            result.edges.push(edge);
        }
    }

    return result;
}

function parseIsonLine(line: string): string[] {
    const parts: string[] = [];
    let current = '';
    let inQuote = false;
    let quoteChar = '';

    for (const char of line) {
        if (inQuote) {
            if (char === quoteChar) {
                inQuote = false;
                parts.push(current);
                current = '';
            } else {
                current += char;
            }
        } else if (char === '"' || char === "'") {
            inQuote = true;
            quoteChar = char;
        } else if (char === ' ' || char === '\t') {
            if (current) {
                parts.push(current);
                current = '';
            }
        } else {
            current += char;
        }
    }

    if (current) {
        parts.push(current);
    }

    return parts;
}

function parseValue(value: string): any {
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (value === 'null' || value === '') return null;

    const num = Number(value);
    if (!isNaN(num)) return num;

    return value;
}

function parseNodeRef(ref: string): { type: string; id: string } {
    const parts = ref.slice(1).split(':');
    return {
        type: parts[0] || 'entity',
        id: parts[1] || ''
    };
}

function formatIson(text: string): string {
    const lines = text.split('\n');
    const formatted: string[] = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Preserve empty lines
        if (!trimmed) {
            formatted.push('');
            continue;
        }

        // Section headers don't need indentation
        if (trimmed.startsWith('graph ') ||
            trimmed === 'directed' ||
            trimmed === 'undirected' ||
            trimmed.startsWith('nodes.') ||
            trimmed.startsWith('edges.')) {
            formatted.push(trimmed);
            continue;
        }

        // Data rows - just trim
        formatted.push(trimmed);
    }

    return formatted.join('\n');
}

interface ValidationError {
    line: number;
    message: string;
}

function validateIson(text: string): ValidationError[] {
    const errors: ValidationError[] = [];
    const lines = text.split('\n');

    let currentSection = '';
    let expectedColumns = 0;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line || line.startsWith('#')) continue;

        if (line.startsWith('nodes.') || line.startsWith('edges.')) {
            currentSection = line;
            expectedColumns = 0;
            continue;
        }

        if (currentSection && expectedColumns === 0) {
            // This should be the header row
            const parts = parseIsonLine(line);
            expectedColumns = parts.length;

            if (currentSection.startsWith('nodes.') && !parts.includes('id')) {
                errors.push({
                    line: i,
                    message: 'Node section must have "id" column'
                });
            }

            if (currentSection.startsWith('edges.')) {
                if (!parts.includes('source')) {
                    errors.push({
                        line: i,
                        message: 'Edge section must have "source" column'
                    });
                }
                if (!parts.includes('target')) {
                    errors.push({
                        line: i,
                        message: 'Edge section must have "target" column'
                    });
                }
            }
            continue;
        }

        // Data row - check column count
        if (currentSection && expectedColumns > 0) {
            const parts = parseIsonLine(line);
            if (parts.length !== expectedColumns) {
                errors.push({
                    line: i,
                    message: `Expected ${expectedColumns} columns, got ${parts.length}`
                });
            }

            // Check node references in edge sections
            if (currentSection.startsWith('edges.')) {
                for (const part of parts) {
                    if (part.startsWith(':') && !part.match(/^:[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_-]+$/)) {
                        errors.push({
                            line: i,
                            message: `Invalid node reference: ${part}`
                        });
                    }
                }
            }
        }
    }

    return errors;
}
