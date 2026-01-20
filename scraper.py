#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集和总结工具
支持头条、Google、Bing 三个平台的新闻搜索
"""

import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, unquote, parse_qs
import time
from typing import List, Dict


class NewsScraper:
    """新闻采集器基类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索新闻，返回标题和URL列表"""
        raise NotImplementedError


class ToutiaoScraper(NewsScraper):
    """头条新闻采集器"""
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索头条新闻"""
        results = []
        try:
            # 头条搜索URL
            search_url = f"https://www.toutiao.com/search/?keyword={quote(keyword)}"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 方法1: 尝试查找script标签中的JSON数据（头条主要使用这种方式）
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and ('window._SSR_HYDRATED_DATA' in script.string or 'articleList' in script.string):
                        try:
                            # 尝试提取JSON数据
                            script_text = script.string
                            # 查找JSON对象
                            json_match = re.search(r'\{.*\}', script_text, re.DOTALL)
                            if json_match:
                                data = json.loads(json_match.group())
                                # 递归查找包含title和url的数据
                                def extract_items(obj, depth=0):
                                    if depth > 5:  # 限制递归深度
                                        return []
                                    items = []
                                    if isinstance(obj, dict):
                                        # 检查是否包含新闻数据
                                        if 'title' in obj and ('url' in obj or 'article_url' in obj):
                                            title = obj.get('title', '')
                                            url = obj.get('url') or obj.get('article_url') or obj.get('link', '')
                                            if title and url:
                                                items.append({'title': title, 'url': url})
                                        # 递归搜索
                                        for value in obj.values():
                                            items.extend(extract_items(value, depth + 1))
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            items.extend(extract_items(item, depth + 1))
                                    return items
                                
                                items = extract_items(data)
                                for item in items[:10]:
                                    url = item['url']
                                    if not url.startswith('http'):
                                        url = urljoin('https://www.toutiao.com', url)
                                    results.append({
                                        'title': item['title'],
                                        'url': url,
                                        'platform': 'toutiao'
                                    })
                                if results:
                                    break
                        except Exception as e:
                            continue
                
                # 方法2: 如果JSON解析失败，尝试HTML解析
                if not results:
                    # 查找包含链接的标题元素
                    links = soup.find_all('a', href=True)
                    seen_titles = set()
                    
                    for link in links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        # 过滤有效的新闻链接
                        if (title and len(title) > 5 and 
                            ('article' in href or '/i' in href or '/a' in href) and
                            title not in seen_titles):
                            
                            if not href.startswith('http'):
                                href = urljoin('https://www.toutiao.com', href)
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'toutiao'
                            })
                            seen_titles.add(title)
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"头条搜索错误: {e}", file=sys.stderr)
        
        return results[:10]  # 确保最多返回10条


class GoogleScraper(NewsScraper):
    """Google新闻采集器"""
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索Google新闻"""
        results = []
        try:
            # Google新闻搜索URL
            search_url = f"https://www.google.com/search?q={quote(keyword)}&tbm=nws"
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Google新闻结果通常在div.g中
                articles = soup.find_all('div', class_='g')
                
                for article in articles[:10]:  # 限制前10条
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
                        if title and link and link.startswith('http'):
                            results.append({
                                'title': title,
                                'url': link,
                                'platform': 'google'
                            })
                
                # 如果div.g没找到，尝试其他选择器
                if not results:
                    # 尝试查找所有包含新闻的链接
                    news_links = soup.find_all('a', href=lambda x: x and ('/url' in x or x.startswith('http')))
                    seen_urls = set()
                    
                    for link_elem in news_links:
                        title = link_elem.get_text(strip=True)
                        href = link_elem.get('href', '')
                        
                        if href.startswith('/url?q='):
                            href = unquote(href.split('/url?q=')[1].split('&')[0])
                        
                        if title and href and href.startswith('http') and href not in seen_urls:
                            results.append({
                                'title': title,
                                'url': href,
                                'platform': 'google'
                            })
                            seen_urls.add(href)
                            
                            if len(results) >= 10:
                                break
                            
        except Exception as e:
            print(f"Google搜索错误: {e}", file=sys.stderr)
        
        return results[:10]  # 确保最多返回10条


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
        
        return results[:10]  # 确保最多返回10条


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python scraper.py <关键字> [平台列表]")
        print("平台列表: toutiao,google,bing (用逗号分隔)")
        sys.exit(1)
    
    keyword = sys.argv[1]
    platforms_str = sys.argv[2] if len(sys.argv) > 2 else 'toutiao,google,bing'
    platforms = [p.strip().lower() for p in platforms_str.split(',')]
    
    # 创建采集器实例
    scrapers = {
        'toutiao': ToutiaoScraper(),
        'google': GoogleScraper(),
        'bing': BingScraper()
    }
    
    all_results = []
    
    # 遍历每个平台进行搜索
    for platform in platforms:
        if platform not in scrapers:
            print(f"警告: 不支持的平台 '{platform}'，跳过", file=sys.stderr)
            continue
        
        print(f"正在搜索 {platform}...", file=sys.stderr)
        results = scrapers[platform].search(keyword)
        all_results.extend(results)
        
        # 添加延迟避免请求过快
        time.sleep(1)
    
    # 构建输出JSON
    output = {
        'keyword': keyword,
        'total': len(all_results),
        'results': all_results,
        'platforms': platforms
    }
    
    # 输出JSON结果
    json_output = json.dumps(output, ensure_ascii=False, indent=2)
    print(json_output)
    
    # 保存到文件
    with open('results.json', 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print(f"\n结果已保存到 results.json，共找到 {len(all_results)} 条新闻", file=sys.stderr)


if __name__ == '__main__':
    main()
