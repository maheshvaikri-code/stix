/**
 * ISONGraph Playground Application
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const inputTextarea = document.getElementById('inputEditor');
    const outputTextarea = document.getElementById('outputEditor');
    const inputFormat = document.getElementById('inputFormat');
    const outputFormatLabel = document.getElementById('outputFormat');
    const examplesSelect = document.getElementById('examples');

    // Initialize CodeMirror editors
    const inputEditor = CodeMirror.fromTextArea(inputTextarea, {
        mode: 'application/json',
        theme: 'default',
        lineNumbers: true,
        lineWrapping: true,
        matchBrackets: true,
        tabSize: 2,
        viewportMargin: Infinity
    });

    const outputEditor = CodeMirror.fromTextArea(outputTextarea, {
        mode: 'text/x-ison',
        theme: 'default',
        lineNumbers: true,
        lineWrapping: true,
        readOnly: true,
        tabSize: 2,
        viewportMargin: Infinity
    });

    // Buttons
    const convertToIsonBtn = document.getElementById('convertToIson');
    const convertToJsonBtn = document.getElementById('convertToJson');
    const formatBtn = document.getElementById('formatBtn');
    const validateBtn = document.getElementById('validateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const refreshGraphBtn = document.getElementById('refreshGraphBtn');
    const swapBtn = document.getElementById('swapBtn');

    // Stats
    const inputTokensEl = document.getElementById('inputTokens');
    const outputTokensEl = document.getElementById('outputTokens');
    const tokenSavingsEl = document.getElementById('tokenSavings');
    const nodeCountEl = document.getElementById('nodeCount');
    const edgeCountEl = document.getElementById('edgeCount');

    // Validation
    const validationResult = document.getElementById('validationResult');

    // Track current state
    let currentJsonData = null;
    let currentIsonData = null;

    // Examples
    const examples = {
        social: {
            name: "social",
            directed: true,
            nodes: [
                { type: "person", id: "alice", name: "Alice", age: 30, role: "Engineer" },
                { type: "person", id: "bob", name: "Bob", age: 25, role: "Designer" },
                { type: "person", id: "carol", name: "Carol", age: 35, role: "Manager" },
                { type: "company", id: "techcorp", name: "TechCorp", industry: "Technology" }
            ],
            edges: [
                { rel_type: "KNOWS", source: { type: "person", id: "alice" }, target: { type: "person", id: "bob" }, properties: { since: 2020 } },
                { rel_type: "KNOWS", source: { type: "person", id: "bob" }, target: { type: "person", id: "carol" }, properties: { since: 2021 } },
                { rel_type: "WORKS_AT", source: { type: "person", id: "alice" }, target: { type: "company", id: "techcorp" }, properties: { role: "Engineer" } },
                { rel_type: "WORKS_AT", source: { type: "person", id: "bob" }, target: { type: "company", id: "techcorp" }, properties: { role: "Designer" } },
                { rel_type: "MANAGES", source: { type: "person", id: "carol" }, target: { type: "person", id: "alice" }, properties: {} }
            ]
        },
        knowledge: {
            name: "knowledge",
            directed: true,
            nodes: [
                { type: "concept", id: "ai", name: "Artificial Intelligence", description: "Simulation of human intelligence" },
                { type: "concept", id: "ml", name: "Machine Learning", description: "Learning from data patterns" },
                { type: "concept", id: "dl", name: "Deep Learning", description: "Neural network based learning" },
                { type: "concept", id: "nlp", name: "Natural Language Processing", description: "Processing human language" },
                { type: "paper", id: "attention", title: "Attention Is All You Need", year: 2017, citations: 50000 }
            ],
            edges: [
                { rel_type: "SUBFIELD_OF", source: { type: "concept", id: "ml" }, target: { type: "concept", id: "ai" }, properties: {} },
                { rel_type: "SUBFIELD_OF", source: { type: "concept", id: "dl" }, target: { type: "concept", id: "ml" }, properties: {} },
                { rel_type: "SUBFIELD_OF", source: { type: "concept", id: "nlp" }, target: { type: "concept", id: "ai" }, properties: {} },
                { rel_type: "USES", source: { type: "concept", id: "nlp" }, target: { type: "concept", id: "dl" }, properties: {} },
                { rel_type: "INTRODUCES", source: { type: "paper", id: "attention" }, target: { type: "concept", id: "dl" }, properties: { innovation: "Transformer architecture" } }
            ]
        },
        org: {
            name: "organization",
            directed: true,
            nodes: [
                { type: "department", id: "eng", name: "Engineering", budget: 5000000 },
                { type: "department", id: "product", name: "Product", budget: 2000000 },
                { type: "department", id: "sales", name: "Sales", budget: 3000000 },
                { type: "team", id: "frontend", name: "Frontend Team", size: 8 },
                { type: "team", id: "backend", name: "Backend Team", size: 12 },
                { type: "team", id: "ml", name: "ML Team", size: 6 }
            ],
            edges: [
                { rel_type: "CONTAINS", source: { type: "department", id: "eng" }, target: { type: "team", id: "frontend" }, properties: {} },
                { rel_type: "CONTAINS", source: { type: "department", id: "eng" }, target: { type: "team", id: "backend" }, properties: {} },
                { rel_type: "CONTAINS", source: { type: "department", id: "eng" }, target: { type: "team", id: "ml" }, properties: {} },
                { rel_type: "COLLABORATES", source: { type: "team", id: "frontend" }, target: { type: "team", id: "backend" }, properties: { frequency: "daily" } },
                { rel_type: "COLLABORATES", source: { type: "team", id: "ml" }, target: { type: "team", id: "backend" }, properties: { frequency: "weekly" } }
            ]
        },
        movie: {
            name: "movies",
            directed: true,
            nodes: [
                { type: "movie", id: "inception", title: "Inception", year: 2010, rating: 8.8 },
                { type: "movie", id: "interstellar", title: "Interstellar", year: 2014, rating: 8.6 },
                { type: "person", id: "nolan", name: "Christopher Nolan", born: 1970 },
                { type: "person", id: "dicaprio", name: "Leonardo DiCaprio", born: 1974 },
                { type: "person", id: "mcconaughey", name: "Matthew McConaughey", born: 1969 },
                { type: "genre", id: "scifi", name: "Science Fiction" }
            ],
            edges: [
                { rel_type: "DIRECTED", source: { type: "person", id: "nolan" }, target: { type: "movie", id: "inception" }, properties: {} },
                { rel_type: "DIRECTED", source: { type: "person", id: "nolan" }, target: { type: "movie", id: "interstellar" }, properties: {} },
                { rel_type: "ACTED_IN", source: { type: "person", id: "dicaprio" }, target: { type: "movie", id: "inception" }, properties: { role: "Cobb" } },
                { rel_type: "ACTED_IN", source: { type: "person", id: "mcconaughey" }, target: { type: "movie", id: "interstellar" }, properties: { role: "Cooper" } },
                { rel_type: "HAS_GENRE", source: { type: "movie", id: "inception" }, target: { type: "genre", id: "scifi" }, properties: {} },
                { rel_type: "HAS_GENRE", source: { type: "movie", id: "interstellar" }, target: { type: "genre", id: "scifi" }, properties: {} }
            ]
        },
        // Edge-only array format (with_edges.json - complete 50 edges)
        relationships: [
            { source: "person_1", relationship: "KNOWS", target: "person_7", since: 2019, strength: "strong" },
            { source: "person_1", relationship: "KNOWS", target: "person_14", since: 2019, strength: "colleague" },
            { source: "person_1", relationship: "KNOWS", target: "person_21", since: 2019, strength: "acquaintance" },
            { source: "person_1", relationship: "KNOWS", target: "person_28", since: 2019, strength: "mentor" },
            { source: "person_2", relationship: "KNOWS", target: "person_8", since: 2020, strength: "strong" },
            { source: "person_2", relationship: "KNOWS", target: "person_15", since: 2020, strength: "colleague" },
            { source: "person_2", relationship: "KNOWS", target: "person_22", since: 2020, strength: "acquaintance" },
            { source: "person_2", relationship: "KNOWS", target: "person_29", since: 2020, strength: "mentor" },
            { source: "person_2", relationship: "KNOWS", target: "person_36", since: 2020, strength: "friend" },
            { source: "person_3", relationship: "KNOWS", target: "person_9", since: 2021, strength: "strong" },
            { source: "person_3", relationship: "KNOWS", target: "person_16", since: 2021, strength: "colleague" },
            { source: "person_3", relationship: "KNOWS", target: "person_23", since: 2021, strength: "acquaintance" },
            { source: "person_3", relationship: "KNOWS", target: "person_30", since: 2021, strength: "mentor" },
            { source: "person_3", relationship: "KNOWS", target: "person_37", since: 2021, strength: "friend" },
            { source: "person_3", relationship: "KNOWS", target: "person_44", since: 2021, strength: "strong" },
            { source: "person_4", relationship: "KNOWS", target: "person_10", since: 2022, strength: "strong" },
            { source: "person_4", relationship: "KNOWS", target: "person_17", since: 2022, strength: "colleague" },
            { source: "person_4", relationship: "KNOWS", target: "person_24", since: 2022, strength: "acquaintance" },
            { source: "person_5", relationship: "KNOWS", target: "person_11", since: 2023, strength: "strong" },
            { source: "person_5", relationship: "KNOWS", target: "person_18", since: 2023, strength: "colleague" },
            { source: "person_5", relationship: "KNOWS", target: "person_25", since: 2023, strength: "acquaintance" },
            { source: "person_5", relationship: "KNOWS", target: "person_32", since: 2023, strength: "mentor" },
            { source: "person_6", relationship: "KNOWS", target: "person_12", since: 2018, strength: "strong" },
            { source: "person_6", relationship: "KNOWS", target: "person_19", since: 2018, strength: "colleague" },
            { source: "person_6", relationship: "KNOWS", target: "person_26", since: 2018, strength: "acquaintance" },
            { source: "person_6", relationship: "KNOWS", target: "person_33", since: 2018, strength: "mentor" },
            { source: "person_6", relationship: "KNOWS", target: "person_40", since: 2018, strength: "friend" },
            { source: "person_7", relationship: "KNOWS", target: "person_13", since: 2019, strength: "strong" },
            { source: "person_7", relationship: "KNOWS", target: "person_20", since: 2019, strength: "colleague" },
            { source: "person_7", relationship: "KNOWS", target: "person_27", since: 2019, strength: "acquaintance" },
            { source: "person_7", relationship: "KNOWS", target: "person_34", since: 2019, strength: "mentor" },
            { source: "person_7", relationship: "KNOWS", target: "person_41", since: 2019, strength: "friend" },
            { source: "person_7", relationship: "KNOWS", target: "person_48", since: 2019, strength: "strong" },
            { source: "person_8", relationship: "KNOWS", target: "person_14", since: 2020, strength: "strong" },
            { source: "person_8", relationship: "KNOWS", target: "person_21", since: 2020, strength: "colleague" },
            { source: "person_8", relationship: "KNOWS", target: "person_28", since: 2020, strength: "acquaintance" },
            { source: "person_9", relationship: "KNOWS", target: "person_15", since: 2021, strength: "strong" },
            { source: "person_9", relationship: "KNOWS", target: "person_22", since: 2021, strength: "colleague" },
            { source: "person_9", relationship: "KNOWS", target: "person_29", since: 2021, strength: "acquaintance" },
            { source: "person_9", relationship: "KNOWS", target: "person_36", since: 2021, strength: "mentor" },
            { source: "person_10", relationship: "KNOWS", target: "person_16", since: 2022, strength: "strong" },
            { source: "person_10", relationship: "KNOWS", target: "person_23", since: 2022, strength: "colleague" },
            { source: "person_10", relationship: "KNOWS", target: "person_30", since: 2022, strength: "acquaintance" },
            { source: "person_10", relationship: "KNOWS", target: "person_37", since: 2022, strength: "mentor" },
            { source: "person_10", relationship: "KNOWS", target: "person_44", since: 2022, strength: "friend" },
            { source: "person_11", relationship: "KNOWS", target: "person_17", since: 2023, strength: "strong" },
            { source: "person_11", relationship: "KNOWS", target: "person_24", since: 2023, strength: "colleague" },
            { source: "person_11", relationship: "KNOWS", target: "person_31", since: 2023, strength: "acquaintance" },
            { source: "person_11", relationship: "KNOWS", target: "person_38", since: 2023, strength: "mentor" },
            { source: "person_11", relationship: "KNOWS", target: "person_45", since: 2023, strength: "friend" }
        ],
        // Document-Concept mentions graph (concept_mentions.json - complete)
        mentions: {
            name: "query_result",
            directed: true,
            nodes: [
                { type: "Document", id: "doc_1", title: "Vector Databases Explained", author: "Bob Smith", category: "tutorial", publishedAt: "2024-02-02", pages: 11, citations: 3, views: 150 },
                { type: "Document", id: "doc_2", title: "Knowledge Graph Architecture", author: "Carol White", category: "whitepaper", publishedAt: "2024-03-03", pages: 12, citations: 6, views: 200 },
                { type: "Document", id: "doc_3", title: "RAG Systems Deep Dive", author: "David Chen", category: "case-study", publishedAt: "2024-04-04", pages: 13, citations: 9, views: 250 },
                { type: "Document", id: "doc_4", title: "Embedding Models Comparison", author: "Eva Martinez", category: "documentation", publishedAt: "2024-05-05", pages: 14, citations: 12, views: 300 },
                { type: "Document", id: "doc_5", title: "Semantic Search Patterns", author: "Frank Brown", category: "blog", publishedAt: "2024-06-06", pages: 15, citations: 15, views: 350 },
                { type: "Document", id: "doc_6", title: "Graph Algorithms Guide", author: "Grace Lee", category: "report", publishedAt: "2024-07-07", pages: 16, citations: 18, views: 400 },
                { type: "Document", id: "doc_7", title: "Machine Learning at Scale", author: "Henry Wilson", category: "analysis", publishedAt: "2024-08-08", pages: 17, citations: 21, views: 450 },
                { type: "Document", id: "doc_8", title: "Real-time Analytics", author: "Ivy Taylor", category: "research", publishedAt: "2024-09-09", pages: 18, citations: 24, views: 500 },
                { type: "Document", id: "doc_9", title: "Data Pipeline Design", author: "Jack Anderson", category: "tutorial", publishedAt: "2024-10-10", pages: 19, citations: 27, views: 550 },
                { type: "Document", id: "doc_10", title: "Microservices Architecture", author: "Kate Thomas", category: "whitepaper", publishedAt: "2024-11-11", pages: 20, citations: 30, views: 600 },
                { type: "Document", id: "doc_11", title: "API Design Best Practices", author: "Leo Moore", category: "case-study", publishedAt: "2024-12-12", pages: 21, citations: 33, views: 650 },
                { type: "Document", id: "doc_12", title: "Cloud Native Development", author: "Maya Jackson", category: "documentation", publishedAt: "2024-01-13", pages: 22, citations: 36, views: 700 },
                { type: "Document", id: "doc_13", title: "DevOps Transformation", author: "Noah Martin", category: "blog", publishedAt: "2024-02-14", pages: 23, citations: 39, views: 750 },
                { type: "Document", id: "doc_14", title: "Security Best Practices", author: "Olivia Garcia", category: "report", publishedAt: "2024-03-15", pages: 24, citations: 42, views: 800 },
                { type: "Document", id: "doc_15", title: "Performance Optimization", author: "Paul Davis", category: "analysis", publishedAt: "2024-04-16", pages: 25, citations: 45, views: 850 },
                { type: "Document", id: "doc_16", title: "Scalability Patterns", author: "Quinn Miller", category: "research", publishedAt: "2024-05-17", pages: 26, citations: 48, views: 900 },
                { type: "Document", id: "doc_17", title: "Data Modeling Techniques", author: "Rachel Jones", category: "tutorial", publishedAt: "2024-06-18", pages: 27, citations: 51, views: 950 },
                { type: "Concept", id: "concept_1", name: "Neural Networks", domain: "Data Science", importance: "high" },
                { type: "Concept", id: "concept_2", name: "Knowledge Graphs", domain: "Software Engineering", importance: "high" },
                { type: "Concept", id: "concept_3", name: "Vector Embeddings", domain: "Cloud Computing", importance: "high" },
                { type: "Concept", id: "concept_4", name: "Graph Databases", domain: "Security", importance: "high" },
                { type: "Concept", id: "concept_5", name: "Semantic Search", domain: "DevOps", importance: "high" },
                { type: "Concept", id: "concept_6", name: "Machine Learning", domain: "AI", importance: "high" },
                { type: "Concept", id: "concept_7", name: "Deep Learning", domain: "Analytics", importance: "high" },
                { type: "Concept", id: "concept_8", name: "Natural Language Processing", domain: "Big Data", importance: "high" },
                { type: "Concept", id: "concept_9", name: "Computer Vision", domain: "Databases", importance: "high" },
                { type: "Concept", id: "concept_10", name: "Reinforcement Learning", domain: "Machine Learning", importance: "high" },
                { type: "Concept", id: "concept_11", name: "Transfer Learning", domain: "Data Science", importance: "high" },
                { type: "Concept", id: "concept_12", name: "Federated Learning", domain: "Software Engineering", importance: "high" },
                { type: "Concept", id: "concept_13", name: "AutoML", domain: "Cloud Computing", importance: "high" },
                { type: "Concept", id: "concept_14", name: "MLOps", domain: "Security", importance: "high" },
                { type: "Concept", id: "concept_15", name: "Data Engineering", domain: "DevOps", importance: "high" },
                { type: "Concept", id: "concept_16", name: "Feature Engineering", domain: "AI", importance: "medium" },
                { type: "Concept", id: "concept_17", name: "Model Serving", domain: "Analytics", importance: "medium" },
                { type: "Concept", id: "concept_18", name: "A/B Testing", domain: "Big Data", importance: "medium" },
                { type: "Concept", id: "concept_19", name: "Experimentation", domain: "Databases", importance: "medium" },
                { type: "Concept", id: "concept_20", name: "Data Quality", domain: "Machine Learning", importance: "medium" },
                { type: "Concept", id: "concept_21", name: "Data Governance", domain: "Data Science", importance: "medium" },
                { type: "Concept", id: "concept_22", name: "Data Lineage", domain: "Software Engineering", importance: "medium" },
                { type: "Concept", id: "concept_23", name: "Metadata Management", domain: "Cloud Computing", importance: "medium" },
                { type: "Concept", id: "concept_24", name: "Data Catalog", domain: "Security", importance: "medium" },
                { type: "Concept", id: "concept_25", name: "Data Discovery", domain: "DevOps", importance: "medium" },
                { type: "Concept", id: "concept_26", name: "ETL Pipelines", domain: "AI", importance: "medium" },
                { type: "Concept", id: "concept_27", name: "Stream Processing", domain: "Analytics", importance: "medium" },
                { type: "Concept", id: "concept_28", name: "Batch Processing", domain: "Big Data", importance: "medium" },
                { type: "Concept", id: "concept_29", name: "Real-time Analytics", domain: "Databases", importance: "medium" },
                { type: "Concept", id: "concept_30", name: "OLAP", domain: "Machine Learning", importance: "medium" },
                { type: "Concept", id: "concept_31", name: "Data Warehousing", domain: "Data Science", importance: "medium" },
                { type: "Concept", id: "concept_32", name: "Data Lakes", domain: "Software Engineering", importance: "medium" },
                { type: "Concept", id: "concept_34", name: "Data Mesh", domain: "Security", importance: "medium" },
                { type: "Concept", id: "concept_35", name: "Data Fabric", domain: "DevOps", importance: "medium" },
                { type: "Concept", id: "concept_37", name: "Link Prediction", domain: "Analytics", importance: "low" },
                { type: "Concept", id: "concept_38", name: "Community Detection", domain: "Big Data", importance: "low" },
                { type: "Concept", id: "concept_40", name: "Path Finding", domain: "Machine Learning", importance: "low" },
                { type: "Concept", id: "concept_41", name: "Similarity Search", domain: "Data Science", importance: "low" },
                { type: "Concept", id: "concept_42", name: "Approximate Nearest Neighbors", domain: "Software Engineering", importance: "low" },
                { type: "Concept", id: "concept_43", name: "HNSW Index", domain: "Cloud Computing", importance: "low" },
                { type: "Concept", id: "concept_45", name: "Product Quantization", domain: "DevOps", importance: "low" },
                { type: "Concept", id: "concept_48", name: "Dot Product", domain: "Big Data", importance: "low" }
            ],
            edges: [
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_1" }, target: { type: "Concept", id: "concept_2" }, properties: { relevance: 0.892 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_1" }, target: { type: "Concept", id: "concept_15" }, properties: { relevance: 0.634 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_1" }, target: { type: "Concept", id: "concept_28" }, properties: { relevance: 0.607 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_2" }, target: { type: "Concept", id: "concept_3" }, properties: { relevance: 0.667 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_2" }, target: { type: "Concept", id: "concept_16" }, properties: { relevance: 0.636 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_2" }, target: { type: "Concept", id: "concept_29" }, properties: { relevance: 0.694 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_2" }, target: { type: "Concept", id: "concept_42" }, properties: { relevance: 0.654 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_3" }, target: { type: "Concept", id: "concept_4" }, properties: { relevance: 0.768 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_3" }, target: { type: "Concept", id: "concept_17" }, properties: { relevance: 0.610 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_4" }, target: { type: "Concept", id: "concept_5" }, properties: { relevance: 0.828 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_4" }, target: { type: "Concept", id: "concept_18" }, properties: { relevance: 0.698 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_4" }, target: { type: "Concept", id: "concept_31" }, properties: { relevance: 0.670 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_5" }, target: { type: "Concept", id: "concept_6" }, properties: { relevance: 0.841 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_5" }, target: { type: "Concept", id: "concept_19" }, properties: { relevance: 0.676 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_5" }, target: { type: "Concept", id: "concept_32" }, properties: { relevance: 0.612 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_5" }, target: { type: "Concept", id: "concept_45" }, properties: { relevance: 0.665 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_6" }, target: { type: "Concept", id: "concept_7" }, properties: { relevance: 0.636 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_6" }, target: { type: "Concept", id: "concept_20" }, properties: { relevance: 0.615 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_7" }, target: { type: "Concept", id: "concept_8" }, properties: { relevance: 0.641 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_7" }, target: { type: "Concept", id: "concept_21" }, properties: { relevance: 0.634 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_7" }, target: { type: "Concept", id: "concept_34" }, properties: { relevance: 0.644 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_8" }, target: { type: "Concept", id: "concept_9" }, properties: { relevance: 0.612 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_8" }, target: { type: "Concept", id: "concept_22" }, properties: { relevance: 0.681 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_8" }, target: { type: "Concept", id: "concept_35" }, properties: { relevance: 0.659 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_8" }, target: { type: "Concept", id: "concept_48" }, properties: { relevance: 0.683 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_9" }, target: { type: "Concept", id: "concept_10" }, properties: { relevance: 0.634 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_9" }, target: { type: "Concept", id: "concept_23" }, properties: { relevance: 0.646 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_10" }, target: { type: "Concept", id: "concept_11" }, properties: { relevance: 0.684 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_10" }, target: { type: "Concept", id: "concept_24" }, properties: { relevance: 0.653 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_10" }, target: { type: "Concept", id: "concept_37" }, properties: { relevance: 0.632 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_11" }, target: { type: "Concept", id: "concept_12" }, properties: { relevance: 0.879 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_11" }, target: { type: "Concept", id: "concept_25" }, properties: { relevance: 0.684 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_11" }, target: { type: "Concept", id: "concept_38" }, properties: { relevance: 0.682 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_11" }, target: { type: "Concept", id: "concept_1" }, properties: { relevance: 0.601 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_12" }, target: { type: "Concept", id: "concept_13" }, properties: { relevance: 0.819 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_12" }, target: { type: "Concept", id: "concept_26" }, properties: { relevance: 0.606 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_13" }, target: { type: "Concept", id: "concept_14" }, properties: { relevance: 0.770 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_13" }, target: { type: "Concept", id: "concept_27" }, properties: { relevance: 0.660 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_13" }, target: { type: "Concept", id: "concept_40" }, properties: { relevance: 0.628 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_14" }, target: { type: "Concept", id: "concept_15" }, properties: { relevance: 0.632 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_14" }, target: { type: "Concept", id: "concept_28" }, properties: { relevance: 0.602 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_14" }, target: { type: "Concept", id: "concept_41" }, properties: { relevance: 0.658 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_14" }, target: { type: "Concept", id: "concept_4" }, properties: { relevance: 0.691 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_15" }, target: { type: "Concept", id: "concept_16" }, properties: { relevance: 0.818 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_15" }, target: { type: "Concept", id: "concept_29" }, properties: { relevance: 0.612 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_16" }, target: { type: "Concept", id: "concept_17" }, properties: { relevance: 0.815 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_16" }, target: { type: "Concept", id: "concept_30" }, properties: { relevance: 0.647 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_16" }, target: { type: "Concept", id: "concept_43" }, properties: { relevance: 0.677 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_17" }, target: { type: "Concept", id: "concept_18" }, properties: { relevance: 0.773 } },
                { rel_type: "MENTIONS", source: { type: "Document", id: "doc_17" }, target: { type: "Concept", id: "concept_31" }, properties: { relevance: 0.681 } }
            ]
        }
    };

    // Initialize graph visualization
    GraphVis.init('graphContainer');

    // Initialize with default JSON example
    loadExample('social');

    // Helper to normalize JSON data structure
    function normalizeJsonData(json) {
        // Build node lookup map for resolving numeric/string IDs in edges
        const buildNodeMap = (nodes) => {
            const map = {};
            for (const node of nodes || []) {
                map[node.id] = node;
                map[String(node.id)] = node;
            }
            return map;
        };

        // Helper to resolve edge source/target
        const resolveNodeRef = (ref, nodeMap) => {
            if (ref && typeof ref === 'object' && ref.id !== undefined) {
                return { type: ref.type || 'entity', id: ref.id };
            }
            const node = nodeMap[ref] || nodeMap[String(ref)];
            if (node) {
                return { type: node.type || 'entity', id: node.id };
            }
            return { type: 'entity', id: ref };
        };

        // Normalize edge format
        const normalizeEdge = (e, nodeMap) => {
            const sourceRef = resolveNodeRef(e.source, nodeMap);
            const targetRef = resolveNodeRef(e.target, nodeMap);

            const properties = e.properties || {};
            const excludeKeys = ['source', 'target', 'relationship', 'relation', 'rel_type', 'type', 'properties'];
            for (const [k, v] of Object.entries(e)) {
                if (!excludeKeys.includes(k)) {
                    properties[k] = v;
                }
            }

            return {
                rel_type: e.rel_type || e.relation || e.relationship || e.type || 'RELATED_TO',
                source: sourceRef,
                target: targetRef,
                properties
            };
        };

        if (Array.isArray(json)) {
            const firstItem = json[0];
            if (firstItem && firstItem.source !== undefined && firstItem.target !== undefined) {
                // Array of edges - extract nodes from source/target
                const nodeIds = new Set();
                const edges = json.map(e => {
                    const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
                    const targetId = typeof e.target === 'object' ? e.target.id : e.target;
                    const sourceType = typeof e.source === 'object' ? e.source.type : 'entity';
                    const targetType = typeof e.target === 'object' ? e.target.type : 'entity';

                    nodeIds.add(JSON.stringify({ type: sourceType, id: sourceId }));
                    nodeIds.add(JSON.stringify({ type: targetType, id: targetId }));

                    const properties = {};
                    for (const [k, v] of Object.entries(e)) {
                        if (!['source', 'target', 'relationship', 'relation', 'rel_type', 'type'].includes(k)) {
                            properties[k] = v;
                        }
                    }

                    return {
                        rel_type: e.rel_type || e.relation || e.relationship || e.type || 'RELATED_TO',
                        source: { type: sourceType, id: sourceId },
                        target: { type: targetType, id: targetId },
                        properties
                    };
                });

                const nodes = Array.from(nodeIds).map(s => {
                    const { type, id } = JSON.parse(s);
                    return { type, id, name: String(id) };
                });

                return { nodes, edges };
            } else {
                return { nodes: json, edges: [] };
            }
        } else if (json && typeof json === 'object' && !json.nodes && (json.type || json.id)) {
            return { nodes: [json], edges: [] };
        } else if (json && json.nodes && json.edges) {
            // Standard format - normalize edges to handle numeric IDs and various field names
            const nodeMap = buildNodeMap(json.nodes);
            const normalizedEdges = json.edges.map(e => normalizeEdge(e, nodeMap));
            return {
                ...json,
                edges: normalizedEdges
            };
        }
        return json;
    }

    // JSON → ISON: Convert JSON input to ISON output
    convertToIsonBtn.addEventListener('click', () => {
        try {
            let json = JSON.parse(inputEditor.getValue());

            // Normalize data structure
            json = normalizeJsonData(json);

            const ison = ISONConverter.jsonToIson(json);

            currentJsonData = json;
            currentIsonData = ison;

            outputEditor.setValue(ison);
            inputEditor.setOption('mode', 'application/json');
            outputEditor.setOption('mode', 'text/x-ison');
            inputFormat.value = 'json';
            outputFormatLabel.textContent = 'ISON';

            updateStats('json', 'ison');

            // Build graph from ISON output (convert back to JSON for visualization)
            const graphData = ISONConverter.isonToJson(ison);
            updateGraph(graphData);
            hideValidation();
        } catch (e) {
            showError('Invalid JSON: ' + e.message);
        }
    });

    // ISON → JSON: Convert ISON input to JSON output
    convertToJsonBtn.addEventListener('click', () => {
        try {
            const ison = inputEditor.getValue();
            const json = ISONConverter.isonToJson(ison);

            if (!json.nodes || json.nodes.length === 0) {
                showError('No valid ISON data found. Input should start with "graph" or "nodes." sections.');
                return;
            }

            currentIsonData = ison;
            currentJsonData = json;

            outputEditor.setValue(JSON.stringify(json, null, 2));
            inputEditor.setOption('mode', 'text/x-ison');
            outputEditor.setOption('mode', 'application/json');
            inputFormat.value = 'ison';
            outputFormatLabel.textContent = 'JSON';

            updateStats('ison', 'json');
            updateGraph(json);
            hideValidation();
        } catch (e) {
            showError('Invalid ISON: ' + e.message);
        }
    });

    // Swap button - swap input and output
    if (swapBtn) {
        swapBtn.addEventListener('click', () => {
            const tempValue = inputEditor.getValue();
            const tempFormat = inputFormat.value;
            const tempMode = inputEditor.getOption('mode');

            inputEditor.setValue(outputEditor.getValue());
            outputEditor.setValue(tempValue);

            // Swap modes
            inputEditor.setOption('mode', outputEditor.getOption('mode'));
            outputEditor.setOption('mode', tempMode);

            // Swap formats
            if (tempFormat === 'json') {
                inputFormat.value = 'ison';
                outputFormatLabel.textContent = 'JSON';
            } else {
                inputFormat.value = 'json';
                outputFormatLabel.textContent = 'ISON';
            }

            updateStatsFromEditors();
            hideValidation();
        });
    }

    // Format button
    formatBtn.addEventListener('click', () => {
        const format = inputFormat.value;
        if (format === 'json') {
            try {
                const json = JSON.parse(inputEditor.getValue());
                inputEditor.setValue(JSON.stringify(json, null, 2));
            } catch (e) {
                showError('Failed to format JSON: ' + e.message);
            }
        } else {
            // Basic ISON formatting - trim lines
            const lines = inputEditor.getValue().split('\n');
            const formatted = lines.map(line => line.trim()).filter(l => l).join('\n');
            inputEditor.setValue(formatted);
        }
    });

    // Validate button
    validateBtn.addEventListener('click', () => {
        const format = inputFormat.value;
        if (format === 'json') {
            try {
                JSON.parse(inputEditor.getValue());
                showValid();
            } catch (e) {
                showInvalid([{ line: 1, message: e.message }]);
            }
        } else {
            const errors = ISONConverter.validate(inputEditor.getValue());
            if (errors.length === 0) {
                showValid();
            } else {
                showInvalid(errors);
            }
        }
    });

    // Copy button
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(outputEditor.getValue()).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = originalText;
            }, 1500);
        });
    });

    // Download button
    downloadBtn.addEventListener('click', () => {
        const format = outputFormatLabel.textContent.toLowerCase();
        const extension = format === 'ison' ? '.ison' : '.json';
        const blob = new Blob([outputEditor.getValue()], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `graph${extension}`;
        a.click();
        URL.revokeObjectURL(url);
    });

    // Examples dropdown
    examplesSelect.addEventListener('change', () => {
        if (examplesSelect.value) {
            loadExample(examplesSelect.value);
        }
        examplesSelect.value = '';
    });

    // Refresh graph button - builds graph from OUTPUT
    refreshGraphBtn.addEventListener('click', () => {
        try {
            let data;
            const outputFormat = outputFormatLabel.textContent;
            if (outputFormat === 'JSON') {
                // Output is JSON
                data = JSON.parse(outputEditor.getValue());
            } else {
                // Output is ISON - convert to JSON for graph
                data = ISONConverter.isonToJson(outputEditor.getValue());
            }
            updateGraph(data);
        } catch (e) {
            console.log('Could not refresh graph:', e.message);
        }
    });

    // Update stats on input change
    inputEditor.on('change', updateStatsFromEditors);

    // Helper functions
    function loadExample(name) {
        const example = examples[name];
        if (!example) return;

        // Normalize the example data (handle edge-only arrays)
        const normalizedData = normalizeJsonData(example);

        currentJsonData = normalizedData;
        const jsonStr = JSON.stringify(example, null, 2);
        const isonStr = ISONConverter.jsonToIson(normalizedData);

        currentIsonData = isonStr;

        inputEditor.setValue(jsonStr);
        outputEditor.setValue(isonStr);
        inputEditor.setOption('mode', 'application/json');
        outputEditor.setOption('mode', 'text/x-ison');
        inputFormat.value = 'json';
        outputFormatLabel.textContent = 'ISON';

        updateStats('json', 'ison');

        // Build graph from ISON output
        const graphData = ISONConverter.isonToJson(isonStr);
        updateGraph(graphData);
        hideValidation();
    }

    function updateStats(inputType, outputType) {
        const inputText = inputEditor.getValue();
        const outputText = outputEditor.getValue();

        const inTokens = ISONConverter.estimateTokens(inputText);
        const outTokens = ISONConverter.estimateTokens(outputText);

        inputTokensEl.textContent = inTokens.toLocaleString();
        outputTokensEl.textContent = outTokens.toLocaleString();

        // Calculate savings (always show JSON vs ISON comparison)
        let jsonTokens, isonTokens;
        if (inputType === 'json') {
            jsonTokens = inTokens;
            isonTokens = outTokens;
        } else {
            jsonTokens = outTokens;
            isonTokens = inTokens;
        }

        if (jsonTokens > 0) {
            const savings = Math.round((1 - isonTokens / jsonTokens) * 100);
            tokenSavingsEl.textContent = savings > 0 ? `${savings}%` : `${savings}%`;
            tokenSavingsEl.parentElement.classList.toggle('highlight', savings > 0);
        } else {
            tokenSavingsEl.textContent = '0%';
        }

        // Count elements from JSON data
        if (currentJsonData) {
            nodeCountEl.textContent = currentJsonData.nodes?.length || 0;
            edgeCountEl.textContent = currentJsonData.edges?.length || 0;
        }
    }

    function updateStatsFromEditors() {
        const inputText = inputEditor.getValue();
        const outputText = outputEditor.getValue();

        const inTokens = ISONConverter.estimateTokens(inputText);
        const outTokens = ISONConverter.estimateTokens(outputText);

        inputTokensEl.textContent = inTokens.toLocaleString();
        outputTokensEl.textContent = outTokens.toLocaleString();

        // Try to count elements
        try {
            let data;
            if (inputFormat.value === 'json') {
                data = JSON.parse(inputText);
                data = normalizeJsonData(data);
            } else {
                data = ISONConverter.isonToJson(inputText);
            }
            nodeCountEl.textContent = data.nodes?.length || 0;
            edgeCountEl.textContent = data.edges?.length || 0;
            currentJsonData = data;
        } catch (e) {
            // Keep previous counts
        }
    }

    function updateGraph(data) {
        if (!data) return;
        try {
            GraphVis.init('graphContainer');
            GraphVis.render(data);
        } catch (e) {
            console.log('Graph render error:', e.message);
        }
    }

    function showValid() {
        validationResult.classList.remove('hidden', 'invalid');
        validationResult.classList.add('valid');
        validationResult.querySelector('.status').textContent = '✓ Valid';
        validationResult.querySelector('.errors').innerHTML = '';
    }

    function showInvalid(errors) {
        validationResult.classList.remove('hidden', 'valid');
        validationResult.classList.add('invalid');
        validationResult.querySelector('.status').textContent = `✗ ${errors.length} error(s) found`;
        validationResult.querySelector('.errors').innerHTML = errors
            .map(e => `<li>Line ${e.line}: ${e.message}</li>`)
            .join('');
    }

    function hideValidation() {
        validationResult.classList.add('hidden');
    }

    function showError(message) {
        showInvalid([{ line: 1, message }]);
    }
});
