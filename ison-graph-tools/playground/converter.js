/**
 * ISON Converter
 * Converts between JSON and ISON formats
 */

const ISONConverter = {
    /**
     * Convert JSON graph to ISON format
     */
    jsonToIson(json) {
        if (typeof json === 'string') {
            json = JSON.parse(json);
        }

        // Handle plain arrays
        if (Array.isArray(json)) {
            // Detect if array contains edges (has source and target) or nodes (has id/type)
            const firstItem = json[0];
            if (firstItem && firstItem.source !== undefined && firstItem.target !== undefined) {
                // Array of edges - extract nodes from source/target references
                const nodeIds = new Set();
                const edges = json.map(e => {
                    const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                    const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                    const sourceType = typeof e.source === 'object' ? e.source.type : 'entity';
                    const targetType = typeof e.target === 'object' ? e.target.type : 'entity';

                    nodeIds.add(JSON.stringify({ type: sourceType, id: sourceId }));
                    nodeIds.add(JSON.stringify({ type: targetType, id: targetId }));

                    // Extract properties (everything except source, target, relationship/rel_type)
                    const properties = {};
                    for (const [k, v] of Object.entries(e)) {
                        if (!['source', 'target', 'relationship', 'rel_type', 'type'].includes(k)) {
                            properties[k] = v;
                        }
                    }

                    return {
                        rel_type: e.relationship || e.rel_type || e.type || 'RELATED_TO',
                        source: { type: sourceType, id: sourceId },
                        target: { type: targetType, id: targetId },
                        properties
                    };
                });

                // Create nodes from unique IDs
                const nodes = Array.from(nodeIds).map(s => {
                    const { type, id } = JSON.parse(s);
                    return { type, id, name: id };
                });

                json = { nodes, edges };
            } else {
                // Array of nodes
                json = {
                    nodes: json,
                    edges: []
                };
            }
        }
        // Handle single object with type/id - wrap as single node
        else if (json && typeof json === 'object' && !json.nodes && (json.type || json.id)) {
            json = {
                nodes: [json],
                edges: []
            };
        }

        const lines = [];

        // Graph header
        if (json.name) {
            lines.push(`graph ${json.name}`);
            lines.push(json.directed !== false ? 'directed' : 'undirected');
            lines.push('');
        }

        // Group nodes by type
        const nodesByType = {};
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
            const keys = new Set(['id']);
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
                    if (typeof v === 'string' && (v.includes(' ') || v.includes('\t'))) {
                        return `"${v.replace(/"/g, '\\"')}"`;
                    }
                    return String(v);
                });
                lines.push(values.join(' '));
            }
            lines.push('');
        }

        // Build node lookup map for resolving numeric/string IDs
        const nodeMap = {};
        for (const node of json.nodes || []) {
            nodeMap[node.id] = node;
        }

        // Helper to resolve source/target to {type, id}
        const resolveNodeRef = (ref) => {
            if (ref && typeof ref === 'object' && ref.id !== undefined) {
                return { type: ref.type || 'entity', id: ref.id };
            }
            // Numeric or string ID - lookup in nodeMap
            const node = nodeMap[ref];
            if (node) {
                return { type: node.type || 'entity', id: node.id };
            }
            // Fallback
            return { type: 'entity', id: ref };
        };

        // Group edges by type
        const edgesByType = {};
        for (const edge of json.edges || []) {
            const type = edge.rel_type || edge.relation || edge.relationship || edge.type || 'RELATED_TO';
            if (!edgesByType[type]) {
                edgesByType[type] = [];
            }
            edgesByType[type].push(edge);
        }

        // Write edge sections
        for (const [type, edges] of Object.entries(edgesByType)) {
            lines.push(`edges.${type}`);

            // Collect property keys (from properties sub-object or directly on edge)
            const keys = new Set(['source', 'target']);
            const excludeKeys = ['source', 'target', 'rel_type', 'relation', 'relationship', 'type', 'properties'];
            for (const edge of edges) {
                // Check properties sub-object
                for (const key of Object.keys(edge.properties || {})) {
                    keys.add(key);
                }
                // Check direct properties on edge
                for (const key of Object.keys(edge)) {
                    if (!excludeKeys.includes(key)) {
                        keys.add(key);
                    }
                }
            }

            const keyList = Array.from(keys);
            lines.push(keyList.join(' '));

            // Write edge data
            for (const edge of edges) {
                const sourceNode = resolveNodeRef(edge.source);
                const targetNode = resolveNodeRef(edge.target);
                const sourceRef = `:${sourceNode.type}:${sourceNode.id}`;
                const targetRef = `:${targetNode.type}:${targetNode.id}`;

                const values = keyList.map(k => {
                    if (k === 'source') return sourceRef;
                    if (k === 'target') return targetRef;
                    // Check properties sub-object first, then direct edge properties
                    const v = edge.properties?.[k] ?? edge[k];
                    if (v === undefined || v === null) return '';
                    return String(v);
                });
                lines.push(values.join(' '));
            }
            lines.push('');
        }

        return lines.join('\n');
    },

    /**
     * Convert ISON to JSON format
     */
    isonToJson(ison) {
        const result = {
            nodes: [],
            edges: []
        };

        const lines = ison.split('\n');
        let currentSection = '';
        let currentType = '';
        let headers = [];

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
            const parts = this.parseLine(trimmed);

            if (headers.length === 0) {
                headers = parts;
                continue;
            }

            // Parse data row
            if (currentSection === 'nodes') {
                const node = { type: currentType };
                for (let i = 0; i < headers.length && i < parts.length; i++) {
                    node[headers[i]] = this.parseValue(parts[i]);
                }
                result.nodes.push(node);
            } else if (currentSection === 'edges') {
                const edge = {
                    rel_type: currentType,
                    properties: {}
                };
                for (let i = 0; i < headers.length && i < parts.length; i++) {
                    const header = headers[i];
                    const value = parts[i];

                    if (header === 'source' || header === 'target') {
                        edge[header] = this.parseNodeRef(value);
                    } else {
                        edge.properties[header] = this.parseValue(value);
                    }
                }
                result.edges.push(edge);
            }
        }

        return result;
    },

    /**
     * Parse a line into parts, handling quoted strings
     */
    parseLine(line) {
        const parts = [];
        let current = '';
        let inQuote = false;
        let quoteChar = '';

        for (const char of line) {
            if (inQuote) {
                if (char === quoteChar) {
                    inQuote = false;
                    parts.push(current);
                    current = '';
                } else if (char === '\\') {
                    // Handle escape sequences
                    continue;
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
    },

    /**
     * Parse a value string to appropriate type
     */
    parseValue(value) {
        if (value === 'true') return true;
        if (value === 'false') return false;
        if (value === 'null' || value === '' || value === 'nil') return null;

        const num = Number(value);
        if (!isNaN(num) && value !== '') return num;

        return value;
    },

    /**
     * Parse a node reference (:type:id)
     */
    parseNodeRef(ref) {
        const parts = ref.slice(1).split(':');
        return {
            type: parts[0] || 'entity',
            id: parts[1] || ''
        };
    },

    /**
     * Validate ISON format
     */
    validate(ison) {
        const errors = [];
        const lines = ison.split('\n');

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

            if (line.startsWith('graph ') || line === 'directed' || line === 'undirected') {
                continue;
            }

            if (currentSection && expectedColumns === 0) {
                // Header row
                const parts = this.parseLine(line);
                expectedColumns = parts.length;

                if (currentSection.startsWith('nodes.') && !parts.includes('id')) {
                    errors.push({
                        line: i + 1,
                        message: 'Node section must have "id" column'
                    });
                }

                if (currentSection.startsWith('edges.')) {
                    if (!parts.includes('source')) {
                        errors.push({
                            line: i + 1,
                            message: 'Edge section must have "source" column'
                        });
                    }
                    if (!parts.includes('target')) {
                        errors.push({
                            line: i + 1,
                            message: 'Edge section must have "target" column'
                        });
                    }
                }
                continue;
            }

            // Data row
            if (currentSection && expectedColumns > 0) {
                const parts = this.parseLine(line);
                if (parts.length !== expectedColumns) {
                    errors.push({
                        line: i + 1,
                        message: `Expected ${expectedColumns} columns, got ${parts.length}`
                    });
                }

                // Check node references
                if (currentSection.startsWith('edges.')) {
                    for (const part of parts) {
                        if (part.startsWith(':') && !part.match(/^:[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_-]+$/)) {
                            errors.push({
                                line: i + 1,
                                message: `Invalid node reference: ${part}`
                            });
                        }
                    }
                }
            }
        }

        return errors;
    },

    /**
     * Estimate token count (approximate)
     */
    estimateTokens(text) {
        // Rough estimate: ~4 characters per token for English text
        // For structured data, use ~3.5 characters per token
        return Math.ceil(text.length / 3.5);
    },

    /**
     * Count nodes and edges in ISON
     */
    countElements(ison) {
        let nodeCount = 0;
        let edgeCount = 0;

        const lines = ison.split('\n');
        let currentSection = '';
        let isHeader = false;

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;

            if (trimmed.startsWith('nodes.')) {
                currentSection = 'nodes';
                isHeader = true;
                continue;
            }

            if (trimmed.startsWith('edges.')) {
                currentSection = 'edges';
                isHeader = true;
                continue;
            }

            if (trimmed.startsWith('graph ') || trimmed === 'directed' || trimmed === 'undirected') {
                continue;
            }

            if (isHeader) {
                isHeader = false;
                continue;
            }

            if (currentSection === 'nodes') {
                nodeCount++;
            } else if (currentSection === 'edges') {
                edgeCount++;
            }
        }

        return { nodeCount, edgeCount };
    }
};

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ISONConverter;
}
