#!/usr/bin/env python3
"""
ISONGraph Data Sources Module

Provides integrations with various data sources for deep research:
- Search Engines: Google, Bing, DuckDuckGo
- Knowledge Bases: Wikipedia, Wikidata
- Academic: arXiv, PubMed, Semantic Scholar
- Social Media: Twitter/X, Reddit, HackerNews
- News: RSS feeds, News APIs

Usage:
    from ison_graph.sources import (
        # Search
        search_google, search_duckduckgo, search_web,

        # Wikipedia
        wikipedia_article, wikipedia_search, wikidata_entity,

        # Academic
        arxiv_search, arxiv_paper, pubmed_search, semantic_scholar_search,

        # Social
        reddit_search, hackernews_top, twitter_search,

        # Aggregated
        research_topic, deep_research
    )

    # Research a topic across all sources
    result = research_topic("transformer neural networks", max_sources=20)
"""

from __future__ import annotations

import json
import re
import time
import hashlib
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from . import ISONGraph, NodeRef


# =============================================================================
# Common Types
# =============================================================================

@dataclass
class SearchResult:
    """A single search result"""
    title: str
    url: str
    snippet: str
    source: str
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceResult:
    """Result from a data source"""
    graph: ISONGraph
    items_found: int
    source_name: str
    query: str
    errors: List[str] = field(default_factory=list)


# =============================================================================
# HTTP Utilities
# =============================================================================

DEFAULT_USER_AGENT = "ISONGraph-Research/1.0 (Knowledge Graph Builder)"
DEFAULT_TIMEOUT = 30


def _fetch_url(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[str]:
    """Fetch URL content"""
    try:
        default_headers = {'User-Agent': DEFAULT_USER_AGENT}
        if headers:
            default_headers.update(headers)

        request = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = 'utf-8'
            content_type = response.headers.get('Content-Type', '')
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[-1].split(';')[0].strip()
            return response.read().decode(charset, errors='replace')
    except Exception as e:
        return None


def _fetch_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[Dict]:
    """Fetch and parse JSON"""
    content = _fetch_url(url, headers, timeout)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    return None


def _make_id(text: str) -> str:
    """Generate stable ID from text"""
    return hashlib.md5(text.encode()).hexdigest()[:12]


# =============================================================================
# Search Engines
# =============================================================================

class DuckDuckGoSearch:
    """DuckDuckGo search (no API key required)"""

    BASE_URL = "https://html.duckduckgo.com/html/"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search DuckDuckGo"""
        results = []

        try:
            # Use HTML endpoint (no API key needed)
            params = urllib.parse.urlencode({'q': query})
            url = f"{self.BASE_URL}?{params}"

            content = _fetch_url(url)
            if not content:
                return results

            # Parse results from HTML
            results = self._parse_results(content, max_results)

        except Exception as e:
            pass

        return results

    def _parse_results(self, html: str, max_results: int) -> List[SearchResult]:
        """Parse search results from DuckDuckGo HTML"""
        results = []

        # Simple regex parsing for result links
        # Pattern for result blocks
        result_pattern = r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        snippet_pattern = r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>'

        links = re.findall(result_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""

            # Clean URL (DuckDuckGo redirects)
            if 'uddg=' in url:
                url = urllib.parse.unquote(url.split('uddg=')[-1].split('&')[0])

            results.append(SearchResult(
                title=self._clean_text(title),
                url=url,
                snippet=self._clean_text(snippet),
                source='duckduckgo',
                rank=i + 1
            ))

        return results

    def _clean_text(self, text: str) -> str:
        """Clean HTML entities and whitespace"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        return ' '.join(text.split())


class BingSearch:
    """Bing search (scraping - for API use Azure Cognitive Services)"""

    BASE_URL = "https://www.bing.com/search"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search Bing"""
        results = []

        try:
            params = urllib.parse.urlencode({'q': query, 'count': max_results})
            url = f"{self.BASE_URL}?{params}"

            content = _fetch_url(url)
            if not content:
                return results

            # Parse results
            results = self._parse_results(content, max_results)

        except Exception:
            pass

        return results

    def _parse_results(self, html: str, max_results: int) -> List[SearchResult]:
        """Parse Bing search results"""
        results = []

        # Pattern for Bing results
        pattern = r'<li class="b_algo"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?<p[^>]*>([^<]+)</p>'

        for i, match in enumerate(re.finditer(pattern, html, re.DOTALL)):
            if i >= max_results:
                break

            url, title, snippet = match.groups()

            results.append(SearchResult(
                title=self._clean_text(title),
                url=url,
                snippet=self._clean_text(snippet),
                source='bing',
                rank=i + 1
            ))

        return results

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        return ' '.join(text.split())


def search_duckduckgo(query: str, max_results: int = 10) -> List[SearchResult]:
    """Search DuckDuckGo"""
    return DuckDuckGoSearch().search(query, max_results)


def search_bing(query: str, max_results: int = 10) -> List[SearchResult]:
    """Search Bing"""
    return BingSearch().search(query, max_results)


def search_web(
    query: str,
    max_results: int = 10,
    engines: List[str] = None
) -> List[SearchResult]:
    """
    Search multiple engines and combine results.

    Args:
        query: Search query
        max_results: Max results per engine
        engines: List of engines ('duckduckgo', 'bing')

    Returns:
        Combined search results
    """
    engines = engines or ['duckduckgo']
    all_results = []
    seen_urls = set()

    for engine in engines:
        if engine == 'duckduckgo':
            results = search_duckduckgo(query, max_results)
        elif engine == 'bing':
            results = search_bing(query, max_results)
        else:
            continue

        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                all_results.append(result)

    return all_results


def search_to_graph(
    query: str,
    max_results: int = 10,
    engines: List[str] = None
) -> ISONGraph:
    """
    Search web and return results as graph.

    Args:
        query: Search query
        max_results: Maximum results
        engines: Search engines to use

    Returns:
        ISONGraph with search results
    """
    graph = ISONGraph("search_results")
    results = search_web(query, max_results, engines)

    # Add query node
    query_id = _make_id(query)
    graph.add_node('query', query_id, text=query, timestamp=datetime.now().isoformat())

    # Add results
    for result in results:
        result_id = _make_id(result.url)

        if not graph.has_node('search_result', result_id):
            graph.add_node('search_result', result_id,
                          title=result.title,
                          url=result.url,
                          snippet=result.snippet,
                          source=result.source,
                          rank=result.rank)

            graph.add_edge('HAS_RESULT', ('query', query_id), ('search_result', result_id),
                          rank=result.rank)

    return graph


# =============================================================================
# Wikipedia / Wikidata
# =============================================================================

class WikipediaAPI:
    """Wikipedia API client"""

    BASE_URL = "https://en.wikipedia.org/api/rest_v1"
    API_URL = "https://en.wikipedia.org/w/api.php"

    def get_article(self, title: str) -> Optional[Dict]:
        """Get Wikipedia article summary"""
        title_encoded = urllib.parse.quote(title.replace(' ', '_'))
        url = f"{self.BASE_URL}/page/summary/{title_encoded}"

        data = _fetch_json(url)
        if data and 'title' in data:
            return {
                'title': data.get('title', ''),
                'extract': data.get('extract', ''),
                'description': data.get('description', ''),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                'image': data.get('thumbnail', {}).get('source', ''),
                'wikidata_id': data.get('wikibase_item', ''),
                'categories': [],
                'links': []
            }
        return None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search Wikipedia"""
        params = urllib.parse.urlencode({
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'format': 'json'
        })
        url = f"{self.API_URL}?{params}"

        data = _fetch_json(url)
        if data and 'query' in data:
            results = []
            for item in data['query'].get('search', []):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': re.sub(r'<[^>]+>', '', item.get('snippet', '')),
                    'page_id': item.get('pageid'),
                    'url': f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item.get('title', '').replace(' ', '_'))}"
                })
            return results
        return []

    def get_links(self, title: str, limit: int = 50) -> List[str]:
        """Get links from a Wikipedia article"""
        params = urllib.parse.urlencode({
            'action': 'query',
            'titles': title,
            'prop': 'links',
            'pllimit': limit,
            'format': 'json'
        })
        url = f"{self.API_URL}?{params}"

        data = _fetch_json(url)
        if data and 'query' in data:
            pages = data['query'].get('pages', {})
            for page_data in pages.values():
                links = page_data.get('links', [])
                return [link.get('title', '') for link in links]
        return []

    def get_categories(self, title: str) -> List[str]:
        """Get categories for a Wikipedia article"""
        params = urllib.parse.urlencode({
            'action': 'query',
            'titles': title,
            'prop': 'categories',
            'cllimit': 50,
            'format': 'json'
        })
        url = f"{self.API_URL}?{params}"

        data = _fetch_json(url)
        if data and 'query' in data:
            pages = data['query'].get('pages', {})
            for page_data in pages.values():
                cats = page_data.get('categories', [])
                return [cat.get('title', '').replace('Category:', '') for cat in cats]
        return []


class WikidataAPI:
    """Wikidata API client"""

    API_URL = "https://www.wikidata.org/w/api.php"
    SPARQL_URL = "https://query.wikidata.org/sparql"

    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """Get Wikidata entity by ID (Q-number)"""
        params = urllib.parse.urlencode({
            'action': 'wbgetentities',
            'ids': entity_id,
            'format': 'json',
            'languages': 'en'
        })
        url = f"{self.API_URL}?{params}"

        data = _fetch_json(url)
        if data and 'entities' in data:
            entity = data['entities'].get(entity_id, {})
            if entity:
                return self._parse_entity(entity)
        return None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search Wikidata entities"""
        params = urllib.parse.urlencode({
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'limit': limit,
            'format': 'json'
        })
        url = f"{self.API_URL}?{params}"

        data = _fetch_json(url)
        if data and 'search' in data:
            results = []
            for item in data['search']:
                results.append({
                    'id': item.get('id', ''),
                    'label': item.get('label', ''),
                    'description': item.get('description', ''),
                    'url': item.get('concepturi', '')
                })
            return results
        return []

    def _parse_entity(self, entity: Dict) -> Dict:
        """Parse Wikidata entity"""
        labels = entity.get('labels', {})
        descriptions = entity.get('descriptions', {})
        claims = entity.get('claims', {})

        result = {
            'id': entity.get('id', ''),
            'label': labels.get('en', {}).get('value', ''),
            'description': descriptions.get('en', {}).get('value', ''),
            'properties': {}
        }

        # Extract key properties
        property_map = {
            'P31': 'instance_of',
            'P279': 'subclass_of',
            'P17': 'country',
            'P131': 'located_in',
            'P569': 'birth_date',
            'P570': 'death_date',
            'P18': 'image',
            'P856': 'website',
            'P373': 'commons_category'
        }

        for prop_id, prop_name in property_map.items():
            if prop_id in claims:
                values = []
                for claim in claims[prop_id]:
                    mainsnak = claim.get('mainsnak', {})
                    datavalue = mainsnak.get('datavalue', {})

                    if datavalue.get('type') == 'wikibase-entityid':
                        values.append(datavalue.get('value', {}).get('id', ''))
                    elif datavalue.get('type') == 'string':
                        values.append(datavalue.get('value', ''))
                    elif datavalue.get('type') == 'time':
                        values.append(datavalue.get('value', {}).get('time', ''))

                if values:
                    result['properties'][prop_name] = values[0] if len(values) == 1 else values

        return result


def wikipedia_article(title: str) -> Optional[Dict]:
    """Get Wikipedia article"""
    return WikipediaAPI().get_article(title)


def wikipedia_search(query: str, limit: int = 10) -> List[Dict]:
    """Search Wikipedia"""
    return WikipediaAPI().search(query, limit)


def wikidata_entity(entity_id: str) -> Optional[Dict]:
    """Get Wikidata entity"""
    return WikidataAPI().get_entity(entity_id)


def wikidata_search(query: str, limit: int = 10) -> List[Dict]:
    """Search Wikidata"""
    return WikidataAPI().search(query, limit)


def wikipedia_to_graph(title: str, include_links: bool = True) -> ISONGraph:
    """
    Convert Wikipedia article to knowledge graph.

    Args:
        title: Article title
        include_links: Include linked articles

    Returns:
        ISONGraph with article knowledge
    """
    graph = ISONGraph("wikipedia")
    api = WikipediaAPI()

    article = api.get_article(title)
    if not article:
        return graph

    # Add main article
    article_id = _make_id(title)
    graph.add_node('article', article_id,
                  title=article['title'],
                  description=article.get('description', ''),
                  extract=article.get('extract', '')[:2000],
                  url=article.get('url', ''),
                  wikidata_id=article.get('wikidata_id', ''))

    # Add categories
    categories = api.get_categories(title)
    for cat in categories[:20]:
        cat_id = _make_id(cat)
        if not graph.has_node('category', cat_id):
            graph.add_node('category', cat_id, name=cat)
        graph.add_edge('IN_CATEGORY', ('article', article_id), ('category', cat_id))

    # Add linked articles
    if include_links:
        links = api.get_links(title, 30)
        for link_title in links:
            link_id = _make_id(link_title)
            if not graph.has_node('article', link_id):
                graph.add_node('article', link_id, title=link_title)
            if not graph.has_edge('LINKS_TO', ('article', article_id), ('article', link_id)):
                graph.add_edge('LINKS_TO', ('article', article_id), ('article', link_id))

    return graph


# =============================================================================
# Academic Sources
# =============================================================================

class ArxivAPI:
    """arXiv API client"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[Dict]:
        """Search arXiv papers"""
        params = urllib.parse.urlencode({
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': 'descending'
        })
        url = f"{self.BASE_URL}?{params}"

        content = _fetch_url(url)
        if not content:
            return []

        return self._parse_feed(content)

    def get_paper(self, arxiv_id: str) -> Optional[Dict]:
        """Get specific paper by arXiv ID"""
        params = urllib.parse.urlencode({
            'id_list': arxiv_id
        })
        url = f"{self.BASE_URL}?{params}"

        content = _fetch_url(url)
        if not content:
            return None

        papers = self._parse_feed(content)
        return papers[0] if papers else None

    def _parse_feed(self, xml_content: str) -> List[Dict]:
        """Parse Atom feed from arXiv"""
        papers = []

        try:
            # Define namespaces
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            root = ET.fromstring(xml_content)

            for entry in root.findall('atom:entry', ns):
                paper = {
                    'id': self._get_text(entry, 'atom:id', ns).split('/')[-1],
                    'title': self._get_text(entry, 'atom:title', ns),
                    'summary': self._get_text(entry, 'atom:summary', ns),
                    'published': self._get_text(entry, 'atom:published', ns),
                    'updated': self._get_text(entry, 'atom:updated', ns),
                    'authors': [],
                    'categories': [],
                    'pdf_url': '',
                    'url': ''
                }

                # Get authors
                for author in entry.findall('atom:author', ns):
                    name = self._get_text(author, 'atom:name', ns)
                    if name:
                        paper['authors'].append(name)

                # Get categories
                for cat in entry.findall('arxiv:primary_category', ns):
                    term = cat.get('term', '')
                    if term:
                        paper['categories'].append(term)

                for cat in entry.findall('atom:category', ns):
                    term = cat.get('term', '')
                    if term and term not in paper['categories']:
                        paper['categories'].append(term)

                # Get links
                for link in entry.findall('atom:link', ns):
                    if link.get('type') == 'application/pdf':
                        paper['pdf_url'] = link.get('href', '')
                    elif link.get('rel') == 'alternate':
                        paper['url'] = link.get('href', '')

                papers.append(paper)

        except ET.ParseError:
            pass

        return papers

    def _get_text(self, element, path: str, ns: Dict) -> str:
        """Get text from XML element"""
        el = element.find(path, ns)
        if el is not None and el.text:
            return ' '.join(el.text.split())
        return ''


class PubMedAPI:
    """PubMed API client"""

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search PubMed"""
        # First get IDs
        params = urllib.parse.urlencode({
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json'
        })
        url = f"{self.SEARCH_URL}?{params}"

        data = _fetch_json(url)
        if not data or 'esearchresult' not in data:
            return []

        ids = data['esearchresult'].get('idlist', [])
        if not ids:
            return []

        # Fetch details
        return self._fetch_details(ids)

    def _fetch_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch paper details by PMIDs"""
        params = urllib.parse.urlencode({
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml'
        })
        url = f"{self.FETCH_URL}?{params}"

        content = _fetch_url(url)
        if not content:
            return []

        return self._parse_xml(content)

    def _parse_xml(self, xml_content: str) -> List[Dict]:
        """Parse PubMed XML response"""
        papers = []

        try:
            root = ET.fromstring(xml_content)

            for article in root.findall('.//PubmedArticle'):
                paper = {
                    'pmid': '',
                    'title': '',
                    'abstract': '',
                    'authors': [],
                    'journal': '',
                    'pub_date': '',
                    'doi': '',
                    'url': ''
                }

                # Get PMID
                pmid = article.find('.//PMID')
                if pmid is not None:
                    paper['pmid'] = pmid.text or ''
                    paper['url'] = f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"

                # Get title
                title = article.find('.//ArticleTitle')
                if title is not None:
                    paper['title'] = title.text or ''

                # Get abstract
                abstract_texts = article.findall('.//AbstractText')
                paper['abstract'] = ' '.join(
                    (at.text or '') for at in abstract_texts
                )[:2000]

                # Get authors
                for author in article.findall('.//Author'):
                    last = author.find('LastName')
                    first = author.find('ForeName')
                    if last is not None:
                        name = last.text or ''
                        if first is not None and first.text:
                            name = f"{first.text} {name}"
                        paper['authors'].append(name)

                # Get journal
                journal = article.find('.//Journal/Title')
                if journal is not None:
                    paper['journal'] = journal.text or ''

                # Get DOI
                for aid in article.findall('.//ArticleId'):
                    if aid.get('IdType') == 'doi':
                        paper['doi'] = aid.text or ''
                        break

                papers.append(paper)

        except ET.ParseError:
            pass

        return papers


class SemanticScholarAPI:
    """Semantic Scholar API client"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search papers"""
        params = urllib.parse.urlencode({
            'query': query,
            'limit': limit,
            'fields': 'paperId,title,abstract,authors,year,citationCount,url,openAccessPdf'
        })
        url = f"{self.BASE_URL}/paper/search?{params}"

        data = _fetch_json(url)
        if data and 'data' in data:
            papers = []
            for item in data['data']:
                paper = {
                    'id': item.get('paperId', ''),
                    'title': item.get('title', ''),
                    'abstract': (item.get('abstract') or '')[:2000],
                    'year': item.get('year'),
                    'citation_count': item.get('citationCount', 0),
                    'url': item.get('url', ''),
                    'pdf_url': (item.get('openAccessPdf') or {}).get('url', ''),
                    'authors': [a.get('name', '') for a in item.get('authors', [])]
                }
                papers.append(paper)
            return papers
        return []

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Get paper by Semantic Scholar ID"""
        fields = 'paperId,title,abstract,authors,year,citationCount,url,references,citations'
        url = f"{self.BASE_URL}/paper/{paper_id}?fields={fields}"

        data = _fetch_json(url)
        if data:
            return {
                'id': data.get('paperId', ''),
                'title': data.get('title', ''),
                'abstract': (data.get('abstract') or '')[:2000],
                'year': data.get('year'),
                'citation_count': data.get('citationCount', 0),
                'url': data.get('url', ''),
                'authors': [a.get('name', '') for a in data.get('authors', [])],
                'references': [r.get('paperId') for r in data.get('references', []) if r.get('paperId')],
                'citations': [c.get('paperId') for c in data.get('citations', []) if c.get('paperId')]
            }
        return None


def arxiv_search(query: str, max_results: int = 10) -> List[Dict]:
    """Search arXiv papers"""
    return ArxivAPI().search(query, max_results)


def arxiv_paper(arxiv_id: str) -> Optional[Dict]:
    """Get arXiv paper by ID"""
    return ArxivAPI().get_paper(arxiv_id)


def pubmed_search(query: str, max_results: int = 10) -> List[Dict]:
    """Search PubMed"""
    return PubMedAPI().search(query, max_results)


def semantic_scholar_search(query: str, limit: int = 10) -> List[Dict]:
    """Search Semantic Scholar"""
    return SemanticScholarAPI().search(query, limit)


def academic_search(
    query: str,
    max_results: int = 10,
    sources: List[str] = None
) -> List[Dict]:
    """
    Search multiple academic sources.

    Args:
        query: Search query
        max_results: Max results per source
        sources: List of sources ('arxiv', 'pubmed', 'semantic_scholar')

    Returns:
        Combined list of papers
    """
    sources = sources or ['arxiv', 'semantic_scholar']
    all_papers = []

    for source in sources:
        if source == 'arxiv':
            papers = arxiv_search(query, max_results)
            for p in papers:
                p['source'] = 'arxiv'
            all_papers.extend(papers)
        elif source == 'pubmed':
            papers = pubmed_search(query, max_results)
            for p in papers:
                p['source'] = 'pubmed'
            all_papers.extend(papers)
        elif source == 'semantic_scholar':
            papers = semantic_scholar_search(query, max_results)
            for p in papers:
                p['source'] = 'semantic_scholar'
            all_papers.extend(papers)

    return all_papers


def academic_to_graph(query: str, max_results: int = 10) -> ISONGraph:
    """
    Search academic papers and return as graph.

    Args:
        query: Search query
        max_results: Maximum results per source

    Returns:
        ISONGraph with papers and relationships
    """
    graph = ISONGraph("academic_research")

    # Add query node
    query_id = _make_id(query)
    graph.add_node('query', query_id, text=query, timestamp=datetime.now().isoformat())

    papers = academic_search(query, max_results)

    for paper in papers:
        paper_id = _make_id(paper.get('id') or paper.get('title', ''))

        if not graph.has_node('paper', paper_id):
            graph.add_node('paper', paper_id,
                          title=paper.get('title', ''),
                          abstract=paper.get('abstract', '')[:1000],
                          year=paper.get('year') or paper.get('published', '')[:4],
                          source=paper.get('source', ''),
                          url=paper.get('url', ''),
                          citations=paper.get('citation_count', 0))

            # Add authors
            for author in paper.get('authors', [])[:10]:
                author_id = _make_id(author)
                if not graph.has_node('author', author_id):
                    graph.add_node('author', author_id, name=author)
                if not graph.has_edge('AUTHORED_BY', ('paper', paper_id), ('author', author_id)):
                    graph.add_edge('AUTHORED_BY', ('paper', paper_id), ('author', author_id))

            # Link to query
            graph.add_edge('MATCHES_QUERY', ('paper', paper_id), ('query', query_id))

    return graph


# =============================================================================
# Social Media Sources
# =============================================================================

class RedditAPI:
    """Reddit API client (public endpoints)"""

    BASE_URL = "https://www.reddit.com"

    def search(
        self,
        query: str,
        subreddit: Optional[str] = None,
        limit: int = 25,
        sort: str = "relevance"
    ) -> List[Dict]:
        """Search Reddit posts"""
        if subreddit:
            url = f"{self.BASE_URL}/r/{subreddit}/search.json"
            params = {'q': query, 'restrict_sr': 'on', 'limit': limit, 'sort': sort}
        else:
            url = f"{self.BASE_URL}/search.json"
            params = {'q': query, 'limit': limit, 'sort': sort}

        params_str = urllib.parse.urlencode(params)
        full_url = f"{url}?{params_str}"

        data = _fetch_json(full_url)
        if data and 'data' in data:
            posts = []
            for child in data['data'].get('children', []):
                post = child.get('data', {})
                posts.append({
                    'id': post.get('id', ''),
                    'title': post.get('title', ''),
                    'selftext': (post.get('selftext') or '')[:1000],
                    'author': post.get('author', ''),
                    'subreddit': post.get('subreddit', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'url': f"https://reddit.com{post.get('permalink', '')}",
                    'created_utc': post.get('created_utc', 0)
                })
            return posts
        return []

    def get_subreddit_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25
    ) -> List[Dict]:
        """Get posts from a subreddit"""
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json?limit={limit}"

        data = _fetch_json(url)
        if data and 'data' in data:
            posts = []
            for child in data['data'].get('children', []):
                post = child.get('data', {})
                posts.append({
                    'id': post.get('id', ''),
                    'title': post.get('title', ''),
                    'selftext': (post.get('selftext') or '')[:1000],
                    'author': post.get('author', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'url': f"https://reddit.com{post.get('permalink', '')}"
                })
            return posts
        return []


class HackerNewsAPI:
    """Hacker News API client"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    ALGOLIA_URL = "https://hn.algolia.com/api/v1"

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search HN stories"""
        params = urllib.parse.urlencode({
            'query': query,
            'tags': 'story',
            'hitsPerPage': limit
        })
        url = f"{self.ALGOLIA_URL}/search?{params}"

        data = _fetch_json(url)
        if data and 'hits' in data:
            stories = []
            for hit in data['hits']:
                stories.append({
                    'id': hit.get('objectID', ''),
                    'title': hit.get('title', ''),
                    'url': hit.get('url', ''),
                    'author': hit.get('author', ''),
                    'points': hit.get('points', 0),
                    'num_comments': hit.get('num_comments', 0),
                    'created_at': hit.get('created_at', ''),
                    'hn_url': f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                })
            return stories
        return []

    def get_top_stories(self, limit: int = 30) -> List[Dict]:
        """Get top stories"""
        url = f"{self.BASE_URL}/topstories.json"

        ids = _fetch_json(url)
        if not ids:
            return []

        stories = []
        for story_id in ids[:limit]:
            story = self._get_item(story_id)
            if story:
                stories.append(story)

        return stories

    def get_new_stories(self, limit: int = 30) -> List[Dict]:
        """Get new stories"""
        url = f"{self.BASE_URL}/newstories.json"

        ids = _fetch_json(url)
        if not ids:
            return []

        stories = []
        for story_id in ids[:limit]:
            story = self._get_item(story_id)
            if story:
                stories.append(story)

        return stories

    def _get_item(self, item_id: int) -> Optional[Dict]:
        """Get item by ID"""
        url = f"{self.BASE_URL}/item/{item_id}.json"

        data = _fetch_json(url)
        if data:
            return {
                'id': str(data.get('id', '')),
                'title': data.get('title', ''),
                'url': data.get('url', ''),
                'author': data.get('by', ''),
                'points': data.get('score', 0),
                'num_comments': len(data.get('kids', [])),
                'time': data.get('time', 0),
                'hn_url': f"https://news.ycombinator.com/item?id={data.get('id', '')}"
            }
        return None


def reddit_search(query: str, subreddit: Optional[str] = None, limit: int = 25) -> List[Dict]:
    """Search Reddit"""
    return RedditAPI().search(query, subreddit, limit)


def reddit_subreddit(subreddit: str, sort: str = "hot", limit: int = 25) -> List[Dict]:
    """Get subreddit posts"""
    return RedditAPI().get_subreddit_posts(subreddit, sort, limit)


def hackernews_search(query: str, limit: int = 20) -> List[Dict]:
    """Search Hacker News"""
    return HackerNewsAPI().search(query, limit)


def hackernews_top(limit: int = 30) -> List[Dict]:
    """Get HN top stories"""
    return HackerNewsAPI().get_top_stories(limit)


def hackernews_new(limit: int = 30) -> List[Dict]:
    """Get HN new stories"""
    return HackerNewsAPI().get_new_stories(limit)


def social_to_graph(
    query: str,
    sources: List[str] = None,
    limit: int = 20
) -> ISONGraph:
    """
    Search social sources and return as graph.

    Args:
        query: Search query
        sources: List of sources ('reddit', 'hackernews')
        limit: Max results per source

    Returns:
        ISONGraph with social content
    """
    sources = sources or ['reddit', 'hackernews']
    graph = ISONGraph("social_research")

    query_id = _make_id(query)
    graph.add_node('query', query_id, text=query, timestamp=datetime.now().isoformat())

    for source in sources:
        if source == 'reddit':
            posts = reddit_search(query, limit=limit)
            for post in posts:
                post_id = f"reddit_{post['id']}"
                if not graph.has_node('post', post_id):
                    graph.add_node('post', post_id,
                                  title=post['title'],
                                  content=post['selftext'][:500],
                                  author=post['author'],
                                  subreddit=post['subreddit'],
                                  score=post['score'],
                                  comments=post['num_comments'],
                                  url=post['url'],
                                  source='reddit')
                    graph.add_edge('MATCHES_QUERY', ('post', post_id), ('query', query_id))

        elif source == 'hackernews':
            stories = hackernews_search(query, limit=limit)
            for story in stories:
                story_id = f"hn_{story['id']}"
                if not graph.has_node('post', story_id):
                    graph.add_node('post', story_id,
                                  title=story['title'],
                                  author=story['author'],
                                  points=story['points'],
                                  comments=story['num_comments'],
                                  url=story.get('url') or story['hn_url'],
                                  source='hackernews')
                    graph.add_edge('MATCHES_QUERY', ('post', story_id), ('query', query_id))

    return graph


# =============================================================================
# Aggregated Research
# =============================================================================

@dataclass
class DeepResearchResult:
    """Result from deep research"""
    graph: ISONGraph
    query: str
    sources_searched: List[str]
    total_items: int
    web_results: int
    academic_papers: int
    social_posts: int
    wikipedia_articles: int
    duration_seconds: float
    errors: List[str] = field(default_factory=list)


def research_topic(
    query: str,
    max_results_per_source: int = 10,
    include_web: bool = True,
    include_academic: bool = True,
    include_social: bool = True,
    include_wikipedia: bool = True
) -> DeepResearchResult:
    """
    Research a topic across multiple sources.

    Args:
        query: Research topic/query
        max_results_per_source: Max results per source
        include_web: Search web
        include_academic: Search academic papers
        include_social: Search social media
        include_wikipedia: Search Wikipedia

    Returns:
        DeepResearchResult with combined knowledge graph

    Example:
        >>> result = research_topic("transformer neural networks")
        >>> print(f"Found {result.total_items} items")
        >>> print(result.graph.to_ison())
    """
    start_time = time.time()
    graph = ISONGraph("deep_research")
    errors = []
    sources_searched = []

    web_count = 0
    academic_count = 0
    social_count = 0
    wiki_count = 0

    # Add query node
    query_id = _make_id(query)
    graph.add_node('research_query', query_id,
                  text=query,
                  timestamp=datetime.now().isoformat())

    # Web search
    if include_web:
        try:
            web_graph = search_to_graph(query, max_results_per_source)
            _merge_graphs(graph, web_graph, ('research_query', query_id), 'WEB_RESULT')
            web_count = web_graph.node_count('search_result')
            sources_searched.append('web')
        except Exception as e:
            errors.append(f"Web search error: {e}")

    # Academic search
    if include_academic:
        try:
            academic_graph = academic_to_graph(query, max_results_per_source)
            _merge_graphs(graph, academic_graph, ('research_query', query_id), 'ACADEMIC_RESULT')
            academic_count = academic_graph.node_count('paper')
            sources_searched.extend(['arxiv', 'semantic_scholar'])
        except Exception as e:
            errors.append(f"Academic search error: {e}")

    # Social search
    if include_social:
        try:
            social_graph = social_to_graph(query, limit=max_results_per_source)
            _merge_graphs(graph, social_graph, ('research_query', query_id), 'SOCIAL_RESULT')
            social_count = social_graph.node_count('post')
            sources_searched.extend(['reddit', 'hackernews'])
        except Exception as e:
            errors.append(f"Social search error: {e}")

    # Wikipedia
    if include_wikipedia:
        try:
            wiki_results = wikipedia_search(query, max_results_per_source)
            for result in wiki_results:
                wiki_id = _make_id(result['title'])
                if not graph.has_node('wikipedia', wiki_id):
                    graph.add_node('wikipedia', wiki_id,
                                  title=result['title'],
                                  snippet=result['snippet'],
                                  url=result['url'])
                    graph.add_edge('WIKIPEDIA_RESULT',
                                  ('research_query', query_id),
                                  ('wikipedia', wiki_id))
                    wiki_count += 1
            sources_searched.append('wikipedia')
        except Exception as e:
            errors.append(f"Wikipedia search error: {e}")

    duration = time.time() - start_time

    return DeepResearchResult(
        graph=graph,
        query=query,
        sources_searched=sources_searched,
        total_items=web_count + academic_count + social_count + wiki_count,
        web_results=web_count,
        academic_papers=academic_count,
        social_posts=social_count,
        wikipedia_articles=wiki_count,
        duration_seconds=duration,
        errors=errors
    )


def _merge_graphs(
    target: ISONGraph,
    source: ISONGraph,
    parent_ref: NodeRef,
    edge_type: str
) -> None:
    """Merge source graph into target"""
    # Copy nodes
    for node in source.nodes():
        if node.type != 'query':  # Skip query nodes
            if not target.has_node(node.type, node.id):
                target.add_node(node.type, node.id, **node.properties)

                # Link to parent
                try:
                    target.add_edge(edge_type, parent_ref, (node.type, node.id))
                except:
                    pass

    # Copy edges
    for edge in source.edges():
        if not target.has_edge(edge.rel_type, edge.source, edge.target):
            try:
                target.add_edge(edge.rel_type, edge.source, edge.target, **edge.properties)
            except:
                pass


def deep_research(
    query: str,
    follow_links: bool = False,
    max_depth: int = 1,
    max_total_items: int = 100
) -> DeepResearchResult:
    """
    Deep research with optional link following.

    This performs comprehensive research and optionally follows
    links/references to gather more context.

    Args:
        query: Research query
        follow_links: Whether to follow links for more context
        max_depth: Maximum depth for link following
        max_total_items: Maximum total items to gather

    Returns:
        DeepResearchResult with comprehensive graph
    """
    # First pass - basic research
    result = research_topic(query, max_results_per_source=max_total_items // 4)

    if not follow_links or max_depth < 1:
        return result

    # Follow links for additional context
    from .research import WebResearcher, ResearchOptions

    researcher = WebResearcher(ResearchOptions(
        max_depth=max_depth,
        max_pages=max_total_items - result.total_items,
        extract_entities=True,
        delay_between_requests=0.5
    ))

    # Get URLs from search results
    urls_to_follow = []
    for node in result.graph.nodes('search_result'):
        url = node.properties.get('url', '')
        if url:
            urls_to_follow.append(url)

    # Research top URLs
    for url in urls_to_follow[:10]:
        try:
            researcher.research_url(url, result.graph)
        except:
            pass

    return result


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    'SearchResult',
    'SourceResult',
    'DeepResearchResult',

    # Search Engines
    'search_duckduckgo',
    'search_bing',
    'search_web',
    'search_to_graph',

    # Wikipedia/Wikidata
    'wikipedia_article',
    'wikipedia_search',
    'wikidata_entity',
    'wikidata_search',
    'wikipedia_to_graph',

    # Academic
    'arxiv_search',
    'arxiv_paper',
    'pubmed_search',
    'semantic_scholar_search',
    'academic_search',
    'academic_to_graph',

    # Social
    'reddit_search',
    'reddit_subreddit',
    'hackernews_search',
    'hackernews_top',
    'hackernews_new',
    'social_to_graph',

    # Aggregated Research
    'research_topic',
    'deep_research',

    # API Classes
    'WikipediaAPI',
    'WikidataAPI',
    'ArxivAPI',
    'PubMedAPI',
    'SemanticScholarAPI',
    'RedditAPI',
    'HackerNewsAPI',
    'DuckDuckGoSearch',
    'BingSearch',
]
