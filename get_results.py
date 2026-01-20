#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部获取结果的示例脚本
可以通过GitHub Pages API或GitHub API获取新闻采集结果
"""

import requests
import json
import sys
from typing import Optional, Dict, List


def get_latest_from_pages(repo_url: str) -> Optional[Dict]:
    """
    从GitHub Pages获取最新结果
    
    Args:
        repo_url: GitHub Pages URL，例如 'https://username.github.io/repo-name'
    
    Returns:
        结果字典或None
    """
    try:
        url = f"{repo_url}/api/results_latest.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取失败，状态码: {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return None


def get_from_github_api(owner: str, repo: str, token: Optional[str] = None) -> Optional[List[Dict]]:
    """
    通过GitHub API获取所有Artifacts
    
    Args:
        owner: GitHub用户名或组织名
        repo: 仓库名
        token: GitHub Personal Access Token（可选，用于私有仓库）
    
    Returns:
        Artifacts列表或None
    """
    try:
        headers = {}
        if token:
            headers['Authorization'] = f'token {token}'
        
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/artifacts"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('artifacts', [])
        else:
            print(f"API请求失败，状态码: {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return None


def download_artifact(owner: str, repo: str, artifact_id: int, token: str, output_file: str = 'artifact.zip'):
    """
    下载特定的Artifact
    
    Args:
        owner: GitHub用户名或组织名
        repo: 仓库名
        artifact_id: Artifact ID
        token: GitHub Personal Access Token
        output_file: 输出文件名
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip"
        headers = {'Authorization': f'token {token}'}
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"下载完成: {output_file}")
        else:
            print(f"下载失败，状态码: {response.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)


def main():
    """主函数 - 使用示例"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  1. 从GitHub Pages获取: python get_results.py pages <repo_url>")
        print("  2. 列出Artifacts: python get_results.py list <owner> <repo> [token]")
        print("  3. 下载Artifact: python get_results.py download <owner> <repo> <artifact_id> <token>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'pages':
        if len(sys.argv) < 3:
            print("错误: 需要提供GitHub Pages URL")
            sys.exit(1)
        repo_url = sys.argv[2]
        result = get_latest_from_pages(repo_url)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == 'list':
        if len(sys.argv) < 4:
            print("错误: 需要提供owner和repo")
            sys.exit(1)
        owner = sys.argv[2]
        repo = sys.argv[3]
        token = sys.argv[4] if len(sys.argv) > 4 else None
        artifacts = get_from_github_api(owner, repo, token)
        if artifacts:
            print(f"找到 {len(artifacts)} 个Artifacts:")
            for artifact in artifacts:
                print(f"  - ID: {artifact['id']}, 名称: {artifact['name']}, 创建时间: {artifact['created_at']}")
    
    elif command == 'download':
        if len(sys.argv) < 6:
            print("错误: 需要提供owner, repo, artifact_id和token")
            sys.exit(1)
        owner = sys.argv[2]
        repo = sys.argv[3]
        artifact_id = int(sys.argv[4])
        token = sys.argv[5]
        download_artifact(owner, repo, artifact_id, token)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
