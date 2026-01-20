#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bing新闻采集器
"""

import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
from typing import List, Dict

from base_scraper import NewsScraper


class BingScraper(NewsScraper):
    """Bing新闻采集器"""
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索Bing新闻"""
        results = []
        try:
            # Bing新闻搜索URL
            search_url = f"https://www.bing.com/news/search?q={quote(keyword)}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 方法1: 查找新闻卡片
                articles = soup.find_all(['div', 'article'], class_=lambda x: x and ('news' in x.lower() or 'card' in x.lower() or 'item' in x.lower()))
                
                seen_urls = set()
                
                for article in articles[:15]:  # 多取一些以防过滤后不够
                    # 尝试多种方式查找标题和链接
                    title_elem = None
                    link_elem = None
                    
                    # 查找标题
                    for tag in ['h2', 'h3', 'h4', 'a']:
                        title_elem = article.find(tag, class_=lambda x: x and ('title' in x.lower() if x else False))
                        if title_elem:
                            break
                    if not title_elem:
                        title_elem = article.find(['h2', 'h3', 'h4'])
                    
                    # 查找链接
                    link_elem = article.find('a', href=True)
                    if not link_elem and title_elem and title_elem.name == 'a':
                        link_elem = title_elem
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get('href', '')
                        
                        if link and not link.startswith('http'):
                            link = urljoin('https://www.bing.com', link)
                        
                        # 过滤无效结果
                        if (title and len(title) > 5 and link and 
                            link.startswith('http') and link not in seen_urls):
                            results.append({
                                'title': title,
                                'url': link,
                                'platform': 'bing'
                            })
                            seen_urls.add(link)
                            
                            if len(results) >= 10:
                                break
                
                # 方法2: 如果上面没找到，尝试直接查找所有新闻链接
                if not results:
                    all_links = soup.find_all('a', href=True)
                    for link_elem in all_links:
                        href = link_elem.get('href', '')
                        title = link_elem.get_text(strip=True)
                        
                        # 过滤新闻链接
                        if (title and len(title) > 10 and 
                            ('news' in href.lower() or href.startswith('http')) and
                            href not in seen_urls):
                            
                            if not href.startswith('http'):
                                href = urljoin('https://www.bing.com', href)
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'bing'
                            })
                            seen_urls.add(href)
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"Bing搜索错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        print(f"Bing找到 {len(results)} 条结果", file=sys.stderr)
        return results[:10]  # 确保最多返回10条
