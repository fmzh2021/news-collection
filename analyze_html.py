#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析头条搜索HTML文件结构"""

import re
import json
from bs4 import BeautifulSoup

def analyze_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("=" * 80)
    print("1. 查找所有链接")
    print("=" * 80)
    links = soup.find_all('a', href=True)
    print(f"找到 {len(links)} 个链接\n")
    
    toutiao_links = []
    for i, link in enumerate(links):
        href = link.get('href', '')
        text = link.get_text(strip=True)[:50]
        if 'toutiao' in href.lower() or '/article' in href or '/i' in href:
            toutiao_links.append((href, text))
            if len(toutiao_links) <= 10:
                print(f"{len(toutiao_links)}. href: {href[:100]}")
                print(f"   文本: {text}")
                print()
    
    print(f"\n总共找到 {len(toutiao_links)} 个头条相关链接\n")
    
    print("=" * 80)
    print("2. 查找script标签中的JSON数据")
    print("=" * 80)
    scripts = soup.find_all('script')
    print(f"找到 {len(scripts)} 个script标签\n")
    
    for i, script in enumerate(scripts):
        if script.string:
            content = script.string
            # 查找包含JSON数据的script
            if 'article' in content.lower() or 'title' in content.lower() or '樊振东' in content:
                # 尝试提取JSON
                json_matches = re.findall(r'\{[^{}]*"title"[^{}]*"url"[^{}]*\}', content)
                if json_matches:
                    print(f"Script {i+1} 中找到JSON数据:")
                    for match in json_matches[:3]:
                        print(f"  {match[:200]}...")
                    print()
                
                # 查找URL模式
                url_patterns = [
                    r'https?://[^\s"<>]+toutiao\.com[^\s"<>]*(?:/article/|/i\d+)[^\s"<>]*',
                    r'["\']([^"\']*(?:/article/|/i\d+)[^"\']*)["\']',
                ]
                for pattern in url_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        print(f"Script {i+1} 中找到URL:")
                        for match in matches[:5]:
                            print(f"  {match[:100]}")
                        print()
                        break
    
    print("=" * 80)
    print("3. 查找data属性中的数据")
    print("=" * 80)
    data_elements = soup.find_all(attrs={'data-druid-card-data-id': True})
    print(f"找到 {len(data_elements)} 个data-druid-card-data-id元素\n")
    
    for i, elem in enumerate(data_elements[:5]):
        data_id = elem.get('data-druid-card-data-id', '')
        text_content = elem.get_text(strip=True)[:200]
        print(f"Element {i+1}: data-id={data_id}")
        print(f"  内容: {text_content}")
        print()
    
    print("=" * 80)
    print("4. 查找包含'樊振东'的文本节点")
    print("=" * 80)
    all_text = soup.get_text()
    matches = re.findall(r'.{0,50}樊振东.{0,50}', all_text)
    print(f"找到 {len(matches)} 个包含'樊振东'的文本片段\n")
    for i, match in enumerate(matches[:10]):
        print(f"{i+1}. {match}")
    
    print("\n" + "=" * 80)
    print("5. 查找可能的新闻标题和URL模式")
    print("=" * 80)
    # 查找可能的标题模式
    title_patterns = [
        r'<h[1-6][^>]*>([^<]*樊振东[^<]*)</h[1-6]>',
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]*樊振东[^<]*)</div>',
        r'<a[^>]*>([^<]*樊振东[^<]*)</a>',
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            print(f"找到标题模式: {pattern[:50]}...")
            for match in matches[:5]:
                print(f"  {match[:100]}")
            print()

if __name__ == '__main__':
    analyze_html('樊振东 - 头条搜索.html')
