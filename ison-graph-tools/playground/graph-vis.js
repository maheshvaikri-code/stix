/**
 * ISONGraph Visualization Module
 * D3.js force-directed graph visualization
 */

const GraphVis = {
    svg: null,
    simulation: null,
    container: null,
    width: 0,
    height: 0,

    // Color palette for node types
    colors: [
        '#4e79a7', '#f28e2c', '#e15759', '#76b7b2',
        '#59a14f', '#edc949', '#af7aa1', '#ff9da7',
        '#9c755f', '#bab0ab'
    ],
    typeColorMap: {},
    colorIndex: 0,

    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        // Get dimensions with fallback minimums
        this.width = this.container.clientWidth || 400;
        this.height = this.container.clientHeight || 300;

        // Clear existing
        this.container.innerHTML = '';

        // Create SVG
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', [0, 0, this.width, this.height])
            .attr('preserveAspectRatio', 'xMidYMid meet');

        // Add zoom behavior
        const g = this.svg.append('g').attr('class', 'graph-container');

        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Arrow marker for directed edges
        this.svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#999');

        // Groups for edges and nodes
        g.append('g').attr('class', 'edges');
        g.append('g').attr('class', 'edge-labels');
        g.append('g').attr('class', 'nodes');

        // Reset colors
        this.typeColorMap = {};
        this.colorIndex = 0;
    },

    getColorForType(type) {
        if (!this.typeColorMap[type]) {
            this.typeColorMap[type] = this.colors[this.colorIndex % this.colors.length];
            this.colorIndex++;
        }
        return this.typeColorMap[type];
    },

    render(graphData) {
        if (!this.svg || !graphData) return;

        const nodes = graphData.nodes || [];
        const edges = graphData.edges || [];

        if (nodes.length === 0) {
            this.showEmpty();
            return;
        }

        // Build node maps for edge lookup (by type:id and by id alone)
        const nodeMap = new Map();
        const nodeByIdMap = new Map();
        nodes.forEach(n => {
            const key = `${n.type || 'entity'}:${n.id}`;
            nodeMap.set(key, n);
            // Also map by ID alone for numeric/string references
            nodeByIdMap.set(n.id, n);
            nodeByIdMap.set(String(n.id), n);
        });

        // Helper to resolve edge source/target to nodeMap key
        const resolveNodeKey = (ref) => {
            if (ref && typeof ref === 'object' && ref.id !== undefined) {
                return `${ref.type || 'entity'}:${ref.id}`;
            }
            // Numeric or string ID - lookup in nodeByIdMap
            const node = nodeByIdMap.get(ref) || nodeByIdMap.get(String(ref));
            if (node) {
                return `${node.type || 'entity'}:${node.id}`;
            }
            return `entity:${ref}`;
        };

        // Process edges to use node references
        const links = edges.map(e => {
            const sourceKey = resolveNodeKey(e.source);
            const targetKey = resolveNodeKey(e.target);
            return {
                source: sourceKey,
                target: targetKey,
                rel_type: e.rel_type || e.relation || e.relationship || e.type || 'RELATED_TO',
                properties: e.properties
            };
        }).filter(e => nodeMap.has(e.source) && nodeMap.has(e.target));

        // Process nodes with unique keys
        const processedNodes = nodes.map(n => ({
            id: `${n.type || 'entity'}:${n.id}`,
            type: n.type || 'entity',
            nodeId: n.id,
            label: n.name || n.title || n.label || String(n.id),
            data: n
        }));

        // Update dimensions with fallback minimums
        this.width = this.container.clientWidth || 400;
        this.height = this.container.clientHeight || 300;

        // Update SVG viewBox to match container
        this.svg.attr('viewBox', [0, 0, this.width, this.height]);

        // Create simulation with centered force
        this.simulation = d3.forceSimulation(processedNodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-250))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(35))
            .force('x', d3.forceX(this.width / 2).strength(0.05))
            .force('y', d3.forceY(this.height / 2).strength(0.05));

        const g = this.svg.select('.graph-container');

        // Draw edges
        const edgeGroup = g.select('.edges');
        edgeGroup.selectAll('*').remove();

        const link = edgeGroup.selectAll('line')
            .data(links)
            .join('line')
            .attr('class', 'edge')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 2)
            .attr('marker-end', 'url(#arrowhead)');

        // Draw edge labels
        const edgeLabelGroup = g.select('.edge-labels');
        edgeLabelGroup.selectAll('*').remove();

        const edgeLabels = edgeLabelGroup.selectAll('text')
            .data(links)
            .join('text')
            .attr('class', 'edge-label')
            .attr('font-size', '10px')
            .attr('fill', '#666')
            .attr('text-anchor', 'middle')
            .text(d => d.rel_type);

        // Draw nodes
        const nodeGroup = g.select('.nodes');
        nodeGroup.selectAll('*').remove();

        const node = nodeGroup.selectAll('g')
            .data(processedNodes)
            .join('g')
            .attr('class', 'node')
            .call(this.drag(this.simulation));

        // Node circles
        node.append('circle')
            .attr('r', 18)
            .attr('fill', d => this.getColorForType(d.type))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);

        // Node labels
        node.append('text')
            .attr('dy', 30)
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .attr('fill', '#333')
            .text(d => d.label);

        // Type labels inside nodes
        node.append('text')
            .attr('dy', 4)
            .attr('text-anchor', 'middle')
            .attr('font-size', '9px')
            .attr('fill', '#fff')
            .attr('font-weight', 'bold')
            .text(d => d.type.substring(0, 3).toUpperCase());

        // Tooltips
        node.append('title')
            .text(d => {
                const props = Object.entries(d.data)
                    .filter(([k]) => k !== 'type' && k !== 'id')
                    .map(([k, v]) => `${k}: ${v}`)
                    .join('\n');
                return `${d.type}:${d.nodeId}\n${props}`;
            });

        // Update positions on simulation tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            edgeLabels
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Build legend
        this.updateLegend();
    },

    drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    },

    updateLegend() {
        const legendContainer = document.getElementById('graphLegend');
        if (!legendContainer) return;

        legendContainer.innerHTML = '';

        Object.entries(this.typeColorMap).forEach(([type, color]) => {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = `<span class="legend-color" style="background:${color}"></span>${type}`;
            legendContainer.appendChild(item);
        });
    },

    showEmpty() {
        // Update dimensions
        this.width = this.container.clientWidth || 400;
        this.height = this.container.clientHeight || 300;
        this.svg.attr('viewBox', [0, 0, this.width, this.height]);

        const g = this.svg.select('.graph-container');
        g.selectAll('*').remove();

        g.append('text')
            .attr('x', this.width / 2)
            .attr('y', this.height / 2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('fill', '#999')
            .attr('font-size', '14px')
            .text('No graph data to display');
    },

    clear() {
        if (this.simulation) {
            this.simulation.stop();
        }
        if (this.svg) {
            this.svg.select('.graph-container').selectAll('*').remove();
        }
        this.typeColorMap = {};
        this.colorIndex = 0;
    }
};
