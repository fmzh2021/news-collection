#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google新闻采集器
支持使用Playwright获取动态加载的内容，确保结果与浏览器一致
"""

import sys
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, parse_qs
from typing import List, Dict

# 尝试导入Playwright（可选）
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("提示: Playwright未安装，Google动态内容可能无法获取。安装: pip install playwright && playwright install chromium", file=sys.stderr)

from base_scraper import NewsScraper


class GoogleScraper(NewsScraper):
    """Google新闻采集器"""
    
    def search_with_playwright(self, keyword: str) -> List[Dict]:
        """使用Playwright获取动态加载的内容，确保结果与浏览器一致"""
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                
                # 设置额外的HTTP头
                page.set_extra_http_headers({
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                })
                
                # Google新闻搜索URL
                search_url = f"https://www.google.com/search?q={quote(keyword)}&tbm=nws"
                print(f"使用Playwright访问Google: {search_url}", file=sys.stderr)
                
                try:
                    # 加载页面
                    page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
                    print("DOM内容加载完成", file=sys.stderr)
                    
                    # 等待网络空闲
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                        print("网络请求完成", file=sys.stderr)
                    except PlaywrightTimeoutError:
                        print("网络请求超时，继续处理", file=sys.stderr)
                    
                    # 等待JavaScript执行
                    page.wait_for_timeout(2000)
                    print("等待JavaScript执行...", file=sys.stderr)
                    
                    # 等待搜索结果出现
                    selectors_to_wait = [
                        'div.g',  # Google搜索结果容器
                        'div[data-ved]',  # Google搜索结果项
                        'h3',  # 标题
                        'a[href*="/url"]',  # 链接
                    ]
                    
                    content_loaded = False
                    for selector in selectors_to_wait:
                        try:
                            page.wait_for_selector(selector, timeout=5000, state='attached')
                            print(f"找到内容元素: {selector}", file=sys.stderr)
                            content_loaded = True
                            break
                        except PlaywrightTimeoutError:
                            continue
                    
                    if not content_loaded:
                        print("未找到预期的内容元素，继续处理", file=sys.stderr)
                    
                    # 滚动页面触发懒加载
                    print("滚动页面触发懒加载...", file=sys.stderr)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    
                    # 再次等待网络请求
                    try:
                        page.wait_for_load_state('networkidle', timeout=5000)
                        print("懒加载内容加载完成", file=sys.stderr)
                    except PlaywrightTimeoutError:
                        print("懒加载网络请求超时，继续处理", file=sys.stderr)
                    
                    # 最终等待
                    page.wait_for_timeout(1000)
                    print("页面完全加载完成，开始解析", file=sys.stderr)
                    
                except PlaywrightTimeoutError as e:
                    print(f"页面加载超时: {e}，尝试获取当前内容", file=sys.stderr)
                except Exception as e:
                    print(f"页面加载错误: {e}，继续处理", file=sys.stderr)
                
                # 获取页面HTML
                html_content = page.content()
                print(f"Playwright获取HTML长度: {len(html_content)}", file=sys.stderr)
                
                # 使用Playwright API查找搜索结果
                print("方法1: 使用Playwright API查找搜索结果", file=sys.stderr)
                result_divs = page.query_selector_all('div.g')
                print(f"找到 {len(result_divs)} 个搜索结果", file=sys.stderr)
                
                seen_urls = set()
                
                for div in result_divs[:15]:  # 检查前15个结果
                    try:
                        # 查找标题
                        title_elem = div.query_selector('h3')
                        title = title_elem.inner_text() if title_elem else ''
                        
                        # 查找链接
                        link_elem = div.query_selector('a[href]')
                        if not link_elem:
                            continue
                        
                        href = link_elem.get_attribute('href') or ''
                        
                        # 处理Google的重定向URL
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        elif href.startswith('/url?'):
                            params = parse_qs(href.split('?')[1])
                            if 'q' in params:
                                href = unquote(params['q'][0])
                        
                        # 过滤无效链接
                        if (title and len(title) > 5 and href and 
                            href.startswith('http') and href not in seen_urls):
                            seen_urls.add(href)
                            results.append({
                                'title': title[:200],
                                'url': href,
                                'platform': 'google'
                            })
                            
                            if len(results) >= 10:
                                break
                    except Exception as e:
                        print(f"处理搜索结果时出错: {e}", file=sys.stderr)
                        continue
                
                print(f"从Playwright API获取到 {len(results)} 条结果", file=sys.stderr)
                
                # 如果没找到，尝试从HTML解析
                if not results:
                    print("方法2: 从HTML解析搜索结果", file=sys.stderr)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Google新闻结果通常在div.g中
                    articles = soup.find_all('div', class_='g')
                    
                    for article in articles[:15]:
                        title_elem = article.find('h3')
                        link_elem = article.find('a', href=True)
                        
                        if title_elem and link_elem:
                            title = title_elem.get_text(strip=True)
                            link = link_elem.get('href', '')
                            
                            # Google的链接可能是重定向URL，需要提取真实URL
                            if link.startswith('/url?q='):
                                link = unquote(link.split('/url?q=')[1].split('&')[0])
                            elif link.startswith('/url?'):
                                params = parse_qs(link.split('?')[1])
                                if 'q' in params:
                                    link = unquote(params['q'][0])
                            
                            # 过滤无效链接
                            if (title and link and link.startswith('http') and 
                                link not in seen_urls):
                                seen_urls.add(link)
                                results.append({
                                    'title': title,
                                    'url': link,
                                    'platform': 'google'
                                })
                                
                                if len(results) >= 10:
                                    break
                
                context.close()
                browser.close()
                print(f"Playwright获取到 {len(results)} 条结果", file=sys.stderr)
                
        except Exception as e:
            print(f"Playwright错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        return results[:10]
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索Google新闻"""
        results = []
        
        # 优先使用Playwright获取结果，确保与浏览器一致
        if PLAYWRIGHT_AVAILABLE:
            print("使用Playwright获取Google搜索结果...", file=sys.stderr)
            playwright_results = self.search_with_playwright(keyword)
            if playwright_results:
                return playwright_results
            print("Playwright未获取到结果，尝试使用requests...", file=sys.stderr)
        
        # 备用方法：使用requests（可能结果不完整）
        try:
            # Google新闻搜索URL
            search_url = f"https://www.google.com/search?q={quote(keyword)}&tbm=nws"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Google新闻结果通常在div.g中
                articles = soup.find_all('div', class_='g')
                seen_urls = set()
                
                for article in articles[:15]:  # 多取一些以防过滤后不够
                    title_elem = article.find('h3')
                    link_elem = article.find('a', href=True)
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get('href', '')
                        
                        # Google的链接可能是重定向URL，需要提取真实URL
                        if link.startswith('/url?q='):
                            link = unquote(link.split('/url?q=')[1].split('&')[0])
                        elif link.startswith('/url?'):
                            params = parse_qs(link.split('?')[1])
                            if 'q' in params:
                                link = unquote(params['q'][0])
                        
                        # 过滤无效链接
                        if (title and link and link.startswith('http') and 
                            link not in seen_urls):
                            seen_urls.add(link)
                            results.append({
                                'title': title,
                                'url': link,
                                'platform': 'google'
                            })
                            
                            if len(results) >= 10:
                                break
                
                # 如果div.g没找到，尝试其他选择器
                if not results:
                    # 尝试查找所有包含新闻的链接
                    news_links = soup.find_all('a', href=lambda x: x and ('/url' in x or x.startswith('http')))
                    
                    for link_elem in news_links:
                        title = link_elem.get_text(strip=True)
                        href = link_elem.get('href', '')
                        
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        
                        if (title and len(title) > 10 and href and 
                            href.startswith('http') and href not in seen_urls):
                            seen_urls.add(href)
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'google'
                            })
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"Google搜索错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        print(f"Google找到 {len(results)} 条结果", file=sys.stderr)
        return results[:10]  # 确保最多返回10条
