#!/usr/bin/env python3
"""
ISONGraph Deep Research Module

Provides web research and knowledge extraction capabilities:
- Web page fetching and content extraction
- Entity and relationship extraction from text
- Structured data extraction (JSON-LD, OpenGraph, microdata)
- Link crawling and site mapping
- Research aggregation into knowledge graphs

Usage:
    from ison_graph.research import (
        WebResearcher,
        research_url,
        research_topic,
        extract_entities_from_text,
        crawl_site
    )

    # Quick research on a URL
    graph = research_url("https://example.com/article")

    # Deep research on a topic
    graph = research_topic("machine learning transformers", max_sources=10)

    # Crawl a website
    graph = crawl_site("https://docs.example.com", max_pages=50)
"""

from __future__ import annotations

import json
import re
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Union
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path

from . import ISONGraph, NodeRef


# =============================================================================
# Research Options
# =============================================================================

@dataclass
class ResearchOptions:
    """Options for web research"""

    # Fetching
    timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0
    user_agent: str = "ISONGraph-Research/1.0"

    # Content extraction
    extract_text: bool = True
    extract_links: bool = True
    extract_images: bool = True
    extract_metadata: bool = True
    extract_structured_data: bool = True

    # Entity extraction
    extract_entities: bool = True
    entity_types: List[str] = field(default_factory=lambda: [
        'person', 'organization', 'location', 'date', 'product', 'technology'
    ])

    # Crawling
    max_depth: int = 2
    max_pages: int = 100
    same_domain_only: bool = True
    follow_external_links: bool = False

    # Filtering
    skip_extensions: Set[str] = field(default_factory=lambda: {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.css', '.js',
        '.zip', '.tar', '.gz', '.mp4', '.mp3', '.wav'
    })
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None

    # Output
    include_raw_content: bool = False
    max_content_length: int = 50000


@dataclass
class ResearchResult:
    """Result of a research operation"""
    graph: ISONGraph
    sources: List[str]
    entities_found: int
    relationships_found: int
    pages_crawled: int
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# =============================================================================
# Content Extraction Parser
# =============================================================================

class ContentExtractor(HTMLParser):
    """Extract structured content from HTML"""

    def __init__(self, base_url: str = ""):
        super().__init__()
        self.base_url = base_url

        # Extracted content
        self.title = ""
        self.description = ""
        self.text_content: List[str] = []
        self.links: List[Dict[str, str]] = []
        self.images: List[Dict[str, str]] = []
        self.headings: List[Dict[str, str]] = []
        self.metadata: Dict[str, str] = {}
        self.structured_data: List[Dict] = []
        self.opengraph: Dict[str, str] = {}
        self.twitter_card: Dict[str, str] = {}

        # Parser state
        self._current_tag = ""
        self._current_attrs: Dict[str, str] = {}
        self._in_script = False
        self._in_style = False
        self._in_title = False
        self._script_content = ""
        self._heading_level = 0

    def _resolve_url(self, url: str) -> str:
        """Resolve relative URL to absolute"""
        if not url:
            return ""
        if url.startswith(('http://', 'https://', '//')):
            return url
        return urljoin(self.base_url, url)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self._current_tag = tag.lower()
        self._current_attrs = {k: v or '' for k, v in attrs}

        if tag == 'script':
            self._in_script = True
            self._script_content = ""
            # Check for JSON-LD
            if self._current_attrs.get('type') == 'application/ld+json':
                pass  # Will capture in handle_data
        elif tag == 'style':
            self._in_style = True
        elif tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            self._handle_meta(self._current_attrs)
        elif tag == 'link':
            self._handle_link(self._current_attrs)
        elif tag == 'a':
            href = self._current_attrs.get('href', '')
            if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                self.links.append({
                    'url': self._resolve_url(href),
                    'text': '',  # Will be filled in handle_data
                    'rel': self._current_attrs.get('rel', ''),
                    'title': self._current_attrs.get('title', '')
                })
        elif tag == 'img':
            src = self._current_attrs.get('src', '')
            if src:
                self.images.append({
                    'url': self._resolve_url(src),
                    'alt': self._current_attrs.get('alt', ''),
                    'title': self._current_attrs.get('title', '')
                })
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._heading_level = int(tag[1])

    def handle_endtag(self, tag: str):
        if tag == 'script':
            self._in_script = False
            # Try to parse JSON-LD
            if self._script_content.strip():
                try:
                    data = json.loads(self._script_content)
                    if isinstance(data, dict) and '@type' in data:
                        self.structured_data.append(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and '@type' in item:
                                self.structured_data.append(item)
                except json.JSONDecodeError:
                    pass
            self._script_content = ""
        elif tag == 'style':
            self._in_style = False
        elif tag == 'title':
            self._in_title = False
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._heading_level = 0
        elif tag == 'a':
            self._current_tag = ""

    def handle_data(self, data: str):
        if self._in_script:
            self._script_content += data
            return
        if self._in_style:
            return

        text = data.strip()
        if not text:
            return

        if self._in_title:
            self.title = text
        elif self._heading_level > 0:
            self.headings.append({
                'level': self._heading_level,
                'text': text
            })
            self.text_content.append(text)
        elif self._current_tag == 'a' and self.links:
            # Update last link's text
            self.links[-1]['text'] = text
            self.text_content.append(text)
        elif self._current_tag not in ('script', 'style', 'noscript'):
            self.text_content.append(text)

    def _handle_meta(self, attrs: Dict[str, str]):
        """Handle meta tags"""
        name = attrs.get('name', '').lower()
        prop = attrs.get('property', '').lower()
        content = attrs.get('content', '')

        if not content:
            return

        # Standard meta
        if name == 'description':
            self.description = content
            self.metadata['description'] = content
        elif name == 'keywords':
            self.metadata['keywords'] = content
        elif name == 'author':
            self.metadata['author'] = content
        elif name == 'robots':
            self.metadata['robots'] = content

        # OpenGraph
        if prop.startswith('og:'):
            key = prop[3:]
            self.opengraph[key] = content
            if key == 'title' and not self.title:
                self.title = content
            elif key == 'description' and not self.description:
                self.description = content

        # Twitter Card
        if name.startswith('twitter:'):
            key = name[8:]
            self.twitter_card[key] = content

    def _handle_link(self, attrs: Dict[str, str]):
        """Handle link tags"""
        rel = attrs.get('rel', '')
        href = attrs.get('href', '')

        if rel == 'canonical' and href:
            self.metadata['canonical'] = self._resolve_url(href)

    def get_text(self) -> str:
        """Get cleaned text content"""
        return ' '.join(self.text_content)

    def get_summary(self) -> Dict[str, Any]:
        """Get extraction summary"""
        return {
            'title': self.title,
            'description': self.description,
            'text_length': len(self.get_text()),
            'link_count': len(self.links),
            'image_count': len(self.images),
            'heading_count': len(self.headings),
            'has_structured_data': len(self.structured_data) > 0,
            'has_opengraph': len(self.opengraph) > 0
        }


# =============================================================================
# Entity Extractor
# =============================================================================

class EntityExtractor:
    """Extract entities from text using pattern matching"""

    # Common patterns for entity extraction
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'url': r'https?://[^\s<>"{}|\\^`\[\]]+',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        'date': r'\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
        'money': r'\$[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?)',
        'percentage': r'\b\d+(?:\.\d+)?%',
        'version': r'\bv?\d+(?:\.\d+)+\b',
    }

    # Technology/product keywords
    TECH_KEYWORDS = {
        'python', 'javascript', 'typescript', 'java', 'rust', 'go', 'golang',
        'react', 'vue', 'angular', 'node', 'django', 'flask', 'fastapi',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'api', 'rest', 'graphql', 'grpc', 'websocket',
        'machine learning', 'deep learning', 'neural network', 'nlp', 'llm',
        'gpt', 'bert', 'transformer', 'attention', 'embedding'
    }

    def __init__(self):
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    def extract(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities from text.

        Returns:
            Dict mapping entity type to list of entities
        """
        entities: Dict[str, List[Dict[str, Any]]] = {
            'email': [],
            'url': [],
            'phone': [],
            'date': [],
            'money': [],
            'percentage': [],
            'version': [],
            'technology': [],
            'organization': [],
            'person': []
        }

        text_lower = text.lower()

        # Pattern-based extraction
        for entity_type, pattern in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                entities[entity_type].append({
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })

        # Technology extraction
        for tech in self.TECH_KEYWORDS:
            if tech in text_lower:
                # Find actual case in text
                idx = text_lower.find(tech)
                if idx >= 0:
                    actual = text[idx:idx+len(tech)]
                    entities['technology'].append({
                        'value': actual,
                        'normalized': tech,
                        'start': idx
                    })

        # Organization patterns (basic)
        org_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co|Group|Foundation|Institute|University)\b',
            r'\b(?:Google|Microsoft|Apple|Amazon|Meta|Facebook|Twitter|OpenAI|Anthropic|Netflix|Tesla|SpaceX)\b'
        ]
        for pattern in org_patterns:
            for match in re.finditer(pattern, text):
                entities['organization'].append({
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })

        # Person patterns (basic - names with titles)
        person_patterns = [
            r'\b(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',
            r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b'  # First M. Last
        ]
        for pattern in person_patterns:
            for match in re.finditer(pattern, text):
                entities['person'].append({
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })

        # Deduplicate
        for entity_type in entities:
            seen = set()
            unique = []
            for entity in entities[entity_type]:
                val = entity['value'].lower()
                if val not in seen:
                    seen.add(val)
                    unique.append(entity)
            entities[entity_type] = unique

        return entities

    def extract_from_structured_data(self, data: List[Dict]) -> Dict[str, List[Dict]]:
        """Extract entities from JSON-LD structured data"""
        entities: Dict[str, List[Dict]] = {
            'person': [],
            'organization': [],
            'article': [],
            'product': [],
            'event': [],
            'place': []
        }

        for item in data:
            item_type = item.get('@type', '').lower()

            if 'person' in item_type:
                entities['person'].append({
                    'name': item.get('name', ''),
                    'url': item.get('url', ''),
                    'job_title': item.get('jobTitle', ''),
                    'source': 'json-ld'
                })
            elif 'organization' in item_type or 'company' in item_type:
                entities['organization'].append({
                    'name': item.get('name', ''),
                    'url': item.get('url', ''),
                    'description': item.get('description', ''),
                    'source': 'json-ld'
                })
            elif 'article' in item_type or 'newsarticle' in item_type or 'blogposting' in item_type:
                entities['article'].append({
                    'headline': item.get('headline', ''),
                    'author': self._extract_author(item.get('author')),
                    'date_published': item.get('datePublished', ''),
                    'publisher': self._extract_name(item.get('publisher')),
                    'source': 'json-ld'
                })
            elif 'product' in item_type:
                entities['product'].append({
                    'name': item.get('name', ''),
                    'description': item.get('description', ''),
                    'brand': self._extract_name(item.get('brand')),
                    'source': 'json-ld'
                })
            elif 'event' in item_type:
                entities['event'].append({
                    'name': item.get('name', ''),
                    'start_date': item.get('startDate', ''),
                    'location': self._extract_name(item.get('location')),
                    'source': 'json-ld'
                })
            elif 'place' in item_type or 'localbusiness' in item_type:
                entities['place'].append({
                    'name': item.get('name', ''),
                    'address': self._extract_address(item.get('address')),
                    'source': 'json-ld'
                })

        return entities

    def _extract_author(self, author: Any) -> str:
        if isinstance(author, str):
            return author
        if isinstance(author, dict):
            return author.get('name', '')
        if isinstance(author, list) and author:
            return self._extract_author(author[0])
        return ''

    def _extract_name(self, obj: Any) -> str:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return obj.get('name', '')
        return ''

    def _extract_address(self, addr: Any) -> str:
        if isinstance(addr, str):
            return addr
        if isinstance(addr, dict):
            parts = [
                addr.get('streetAddress', ''),
                addr.get('addressLocality', ''),
                addr.get('addressRegion', ''),
                addr.get('postalCode', ''),
                addr.get('addressCountry', '')
            ]
            return ', '.join(p for p in parts if p)
        return ''


# =============================================================================
# Web Researcher
# =============================================================================

class WebResearcher:
    """
    Deep web research with knowledge graph extraction.

    Example:
        researcher = WebResearcher()

        # Research a single URL
        result = researcher.research_url("https://example.com/article")

        # Research a topic across multiple sources
        result = researcher.research_topic("machine learning")

        # Crawl a website
        result = researcher.crawl_site("https://docs.example.com")
    """

    def __init__(self, options: Optional[ResearchOptions] = None):
        self.options = options or ResearchOptions()
        self.entity_extractor = EntityExtractor()
        self._session = None

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content"""
        try:
            import urllib.request

            headers = {'User-Agent': self.options.user_agent}
            request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request, timeout=self.options.timeout) as response:
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    return None

                charset = 'utf-8'
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].split(';')[0].strip()

                return response.read().decode(charset, errors='replace')

        except Exception as e:
            return None

    def _should_follow_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be followed"""
        parsed = urlparse(url)

        # Check domain
        if self.options.same_domain_only:
            if parsed.netloc != base_domain:
                return False

        # Check extension
        path = parsed.path.lower()
        for ext in self.options.skip_extensions:
            if path.endswith(ext):
                return False

        # Check patterns
        if self.options.exclude_patterns:
            for pattern in self.options.exclude_patterns:
                if re.search(pattern, url):
                    return False

        if self.options.include_patterns:
            for pattern in self.options.include_patterns:
                if re.search(pattern, url):
                    return True
            return False

        return True

    def _url_to_id(self, url: str) -> str:
        """Generate stable ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def research_url(
        self,
        url: str,
        graph: Optional[ISONGraph] = None
    ) -> ISONGraph:
        """
        Research a single URL and extract knowledge.

        Args:
            url: URL to research
            graph: Optional existing graph to add to

        Returns:
            ISONGraph with extracted knowledge
        """
        graph = graph or ISONGraph("research")

        # Fetch content
        html = self._fetch_url(url)
        if not html:
            return graph

        # Extract content
        extractor = ContentExtractor(url)
        extractor.feed(html)

        # Create page node
        page_id = self._url_to_id(url)
        parsed = urlparse(url)

        page_props = {
            'url': url,
            'domain': parsed.netloc,
            'title': extractor.title,
            'description': extractor.description,
            'fetched_at': datetime.now().isoformat()
        }

        if self.options.extract_metadata:
            page_props.update({
                f'meta_{k}': v for k, v in extractor.metadata.items()
            })
            if extractor.opengraph:
                page_props['og_type'] = extractor.opengraph.get('type', '')
                page_props['og_image'] = extractor.opengraph.get('image', '')

        if not graph.has_node('page', page_id):
            graph.add_node('page', page_id, **page_props)

        # Add domain node
        domain_id = parsed.netloc.replace('.', '_')
        if not graph.has_node('domain', domain_id):
            graph.add_node('domain', domain_id,
                          name=parsed.netloc,
                          scheme=parsed.scheme)
        if not graph.has_edge('HOSTED_ON', ('page', page_id), ('domain', domain_id)):
            graph.add_edge('HOSTED_ON', ('page', page_id), ('domain', domain_id))

        # Extract and add entities
        if self.options.extract_entities:
            text = extractor.get_text()
            entities = self.entity_extractor.extract(text)

            # Add structured data entities
            if self.options.extract_structured_data and extractor.structured_data:
                structured_entities = self.entity_extractor.extract_from_structured_data(
                    extractor.structured_data
                )
                for etype, elist in structured_entities.items():
                    entities.setdefault(etype, []).extend(elist)

            self._add_entities_to_graph(graph, entities, page_id)

        # Add links
        if self.options.extract_links:
            for link in extractor.links[:50]:  # Limit links
                link_id = self._url_to_id(link['url'])
                if not graph.has_node('link', link_id):
                    graph.add_node('link', link_id,
                                  url=link['url'],
                                  text=link['text'][:200] if link['text'] else '',
                                  rel=link['rel'])
                if not graph.has_edge('LINKS_TO', ('page', page_id), ('link', link_id)):
                    graph.add_edge('LINKS_TO', ('page', page_id), ('link', link_id))

        # Add headings as structure
        for i, heading in enumerate(extractor.headings[:20]):
            heading_id = f"{page_id}_h{i}"
            if not graph.has_node('heading', heading_id):
                graph.add_node('heading', heading_id,
                              level=heading['level'],
                              text=heading['text'][:200])
                graph.add_edge('HAS_HEADING', ('page', page_id), ('heading', heading_id))

        return graph

    def _add_entities_to_graph(
        self,
        graph: ISONGraph,
        entities: Dict[str, List[Dict]],
        source_page_id: str
    ) -> None:
        """Add extracted entities to graph"""

        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # Generate entity ID
                value = entity.get('value') or entity.get('name', '')
                if not value:
                    continue

                entity_id = hashlib.md5(f"{entity_type}:{value}".encode()).hexdigest()[:12]

                # Add entity node
                if not graph.has_node(entity_type, entity_id):
                    props = {'value': value}
                    for k, v in entity.items():
                        if k not in ('start', 'end') and v:
                            props[k] = str(v)[:500]
                    graph.add_node(entity_type, entity_id, **props)

                # Link to source page
                edge_type = f"MENTIONS_{entity_type.upper()}"
                if not graph.has_edge(edge_type, ('page', source_page_id), (entity_type, entity_id)):
                    graph.add_edge(edge_type, ('page', source_page_id), (entity_type, entity_id))

    def crawl_site(
        self,
        start_url: str,
        graph: Optional[ISONGraph] = None
    ) -> ResearchResult:
        """
        Crawl a website and build knowledge graph.

        Args:
            start_url: Starting URL
            graph: Optional existing graph

        Returns:
            ResearchResult with graph and statistics
        """
        start_time = time.time()
        graph = graph or ISONGraph("crawl")
        errors: List[str] = []

        parsed = urlparse(start_url)
        base_domain = parsed.netloc

        # BFS crawl
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(start_url, 0)]  # (url, depth)
        pages_crawled = 0

        while queue and pages_crawled < self.options.max_pages:
            url, depth = queue.pop(0)

            # Normalize URL
            url = urlunparse(urlparse(url)._replace(fragment=''))

            if url in visited:
                continue
            visited.add(url)

            if depth > self.options.max_depth:
                continue

            if not self._should_follow_url(url, base_domain):
                continue

            # Research this URL
            try:
                self.research_url(url, graph)
                pages_crawled += 1

                # Get links for further crawling
                page_id = self._url_to_id(url)
                if graph.has_node('page', page_id):
                    for link_ref in graph.neighbors(('page', page_id), 'LINKS_TO'):
                        if link_ref[0] == 'link':
                            link_node = graph.get_node('link', link_ref[1])
                            link_url = link_node.properties.get('url', '')
                            if link_url and link_url not in visited:
                                queue.append((link_url, depth + 1))

            except Exception as e:
                errors.append(f"Error crawling {url}: {str(e)}")

            # Rate limiting
            time.sleep(self.options.delay_between_requests)

        duration = time.time() - start_time

        return ResearchResult(
            graph=graph,
            sources=list(visited),
            entities_found=sum(
                graph.node_count(t) for t in graph.node_types()
                if t not in ('page', 'link', 'domain', 'heading')
            ),
            relationships_found=graph.edge_count(),
            pages_crawled=pages_crawled,
            errors=errors,
            duration_seconds=duration
        )

    def research_urls(
        self,
        urls: List[str],
        graph: Optional[ISONGraph] = None
    ) -> ResearchResult:
        """Research multiple URLs"""
        start_time = time.time()
        graph = graph or ISONGraph("research")
        errors: List[str] = []

        for url in urls:
            try:
                self.research_url(url, graph)
            except Exception as e:
                errors.append(f"Error researching {url}: {str(e)}")
            time.sleep(self.options.delay_between_requests)

        duration = time.time() - start_time

        return ResearchResult(
            graph=graph,
            sources=urls,
            entities_found=sum(
                graph.node_count(t) for t in graph.node_types()
                if t not in ('page', 'link', 'domain', 'heading')
            ),
            relationships_found=graph.edge_count(),
            pages_crawled=len(urls),
            errors=errors,
            duration_seconds=duration
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def research_url(
    url: str,
    options: Optional[ResearchOptions] = None
) -> ISONGraph:
    """
    Quick research on a single URL.

    Args:
        url: URL to research
        options: Research options

    Returns:
        ISONGraph with extracted knowledge

    Example:
        >>> graph = research_url("https://en.wikipedia.org/wiki/Machine_learning")
        >>> print(graph.to_ison())
    """
    researcher = WebResearcher(options)
    return researcher.research_url(url)


def research_urls(
    urls: List[str],
    options: Optional[ResearchOptions] = None
) -> ResearchResult:
    """
    Research multiple URLs.

    Args:
        urls: List of URLs to research
        options: Research options

    Returns:
        ResearchResult with combined graph
    """
    researcher = WebResearcher(options)
    return researcher.research_urls(urls)


def crawl_site(
    start_url: str,
    max_pages: int = 50,
    max_depth: int = 2,
    options: Optional[ResearchOptions] = None
) -> ResearchResult:
    """
    Crawl a website and build knowledge graph.

    Args:
        start_url: Starting URL
        max_pages: Maximum pages to crawl
        max_depth: Maximum link depth
        options: Research options

    Returns:
        ResearchResult with site graph

    Example:
        >>> result = crawl_site("https://docs.python.org", max_pages=20)
        >>> print(f"Crawled {result.pages_crawled} pages")
        >>> print(result.graph.to_ison())
    """
    options = options or ResearchOptions()
    options.max_pages = max_pages
    options.max_depth = max_depth

    researcher = WebResearcher(options)
    return researcher.crawl_site(start_url)


def extract_entities_from_text(text: str) -> Dict[str, List[Dict]]:
    """
    Extract entities from text.

    Args:
        text: Text to analyze

    Returns:
        Dict mapping entity type to list of entities

    Example:
        >>> entities = extract_entities_from_text(
        ...     "Google CEO Sundar Pichai announced new AI features."
        ... )
        >>> print(entities['organization'])
        [{'value': 'Google', ...}]
    """
    extractor = EntityExtractor()
    return extractor.extract(text)


def text_to_graph(
    text: str,
    source_name: str = "document"
) -> ISONGraph:
    """
    Convert text to knowledge graph.

    Args:
        text: Text to analyze
        source_name: Name for the source document

    Returns:
        ISONGraph with extracted entities
    """
    graph = ISONGraph("text_analysis")

    # Add document node
    doc_id = hashlib.md5(text[:1000].encode()).hexdigest()[:12]
    graph.add_node('document', doc_id,
                  name=source_name,
                  length=len(text),
                  created_at=datetime.now().isoformat())

    # Extract and add entities
    extractor = EntityExtractor()
    entities = extractor.extract(text)

    for entity_type, entity_list in entities.items():
        for entity in entity_list:
            value = entity.get('value', '')
            if not value:
                continue

            entity_id = hashlib.md5(f"{entity_type}:{value}".encode()).hexdigest()[:12]

            if not graph.has_node(entity_type, entity_id):
                props = {k: str(v)[:500] for k, v in entity.items() if k not in ('start', 'end')}
                graph.add_node(entity_type, entity_id, **props)

            edge_type = f"CONTAINS_{entity_type.upper()}"
            if not graph.has_edge(edge_type, ('document', doc_id), (entity_type, entity_id)):
                graph.add_edge(edge_type, ('document', doc_id), (entity_type, entity_id))

    return graph


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Options and Results
    'ResearchOptions',
    'ResearchResult',

    # Main Classes
    'WebResearcher',
    'ContentExtractor',
    'EntityExtractor',

    # Convenience Functions
    'research_url',
    'research_urls',
    'crawl_site',
    'extract_entities_from_text',
    'text_to_graph',
]
