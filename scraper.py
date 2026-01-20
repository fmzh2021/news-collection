#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集和总结工具
支持头条、Google、Bing 三个平台的新闻搜索
"""

import sys
import json
import os
import time
from datetime import datetime

# 导入各个平台的采集器
from toutiao_scraper import ToutiaoScraper
from google_scraper import GoogleScraper
from bing_scraper import BingScraper


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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_id = os.environ.get('GITHUB_RUN_ID', 'local')
    run_number = os.environ.get('GITHUB_RUN_NUMBER', '0')
    
    # 生成唯一文件名，避免并发覆盖
    filename = f'results_{run_id}_{run_number}_{timestamp}.json'
    
    output = {
        'keyword': keyword,
        'total': len(all_results),
        'results': all_results,
        'platforms': platforms,
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'run_number': run_number,
        'filename': filename
    }
    
    # 输出JSON结果
    json_output = json.dumps(output, ensure_ascii=False, indent=2)
    print(json_output)
    
    # 保存到唯一文件名
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    # 同时保存一个latest.json用于快速访问（可选）
    with open('results_latest.json', 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print(f"\n结果已保存到 {filename} 和 results_latest.json，共找到 {len(all_results)} 条新闻", file=sys.stderr)
    
    # 输出文件名供GitHub Actions使用
    print(f"::set-output name=result_file::{filename}", file=sys.stderr)


if __name__ == '__main__':
    main()
