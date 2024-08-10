import requests
import base64
import time
import socket
from collections import namedtuple

node_urls = [
    'https://raw.githubusercontent.com/yaney01/chromego_merge/main/sub/shadowrocket_base64.txt',
    #'https://raw.githubusercontent.com/njyp/TV/main/jiedian',
    #'https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/base64/mix',
    #'https://chromenodes.marcol.top',
    'https://proxypool.link/vmess/sub',
]

delay_test_url = 'http://cp.cloudflare.com/'
url_test_url = 'https://cp.cloudflare.com/'
download_test_url = 'http://cachefly.cachefly.net/10mb.test'
region_lookup_url = 'http://ip-api.com/json/'

NodeResult = namedtuple('NodeResult', ['node', 'delay', 'url_test', 'download_speed', 'region'])

def fetch_nodes(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        decoded_content = base64.b64decode(response.text).decode('utf-8')
        nodes = decoded_content.splitlines()
        print(f"从 URL {url} 提取的节点：{nodes}")  # 调试输出
        return nodes
    except (requests.RequestException, base64.binascii.Error) as e:
        print(f"从 URL {url} 获取或解码节点时发生错误: {e}")
        return []

def extract_host_from_node(node):
    try:
        if node.startswith('vmess://'):
            node = node[8:]  # 去掉 vmess:// 前缀
        elif node.startswith('trojan://'):
            node = node[8:]  # 去掉 trojan:// 前缀
        elif node.startswith('hysteria://'):
            node = node[10:]  # 去掉 hysteria:// 前缀
        elif node.startswith('hysteria2://'):
            node = node[11:]  # 去掉 hysteria2:// 前缀
        elif node.startswith('shadowsocks://'):
            node = node[11:]  # 去掉 shadowsocks:// 前缀
        else:
            return None
        
        if '@' in node:
            parts = node.split('@')
            return parts[1].split(':')[0]
        else:
            return None
    except Exception as e:
        print(f"解析节点 {node} 时发生错误: {e}")
        return None

def extract_key_from_node(node):
    try:
        if node.startswith('vmess://'):
            node = node[8:]  # 去掉 vmess:// 前缀
            parts = node.split('?')
            address_part = parts[0].split('@')[1]
            return address_part
        elif node.startswith('trojan://'):
            node = node[8:]  # 去掉 trojan:// 前缀
            parts = node.split('?')
            address_part = parts[0].split('@')[1]
            return address_part
        elif node.startswith('hysteria://'):
            node = node[10:]  # 去掉 hysteria:// 前缀
            parts = node.split('?')
            address_part = parts[0]
            return address_part
        elif node.startswith('hysteria2://'):
            node = node[11:]  # 去掉 hysteria2:// 前缀
            parts = node.split('?')
            address_part = parts[0]
            return address_part
        elif node.startswith('shadowsocks://'):
            node = node[11:]  # 去掉 shadowsocks:// 前缀
            parts = node.split('@')
            address_part = parts[1]
            return address_part
        else:
            return None
    except Exception as e:
        print(f"解析节点 {node} 时发生错误: {e}")
        return None

def test_node_delay(node):
    host = extract_host_from_node(node)
    if host is None:
        return None, None
    try:
        start_time = time.time()
        response = requests.get(delay_test_url, timeout=10)
        response.raise_for_status()
        end_time = time.time()
        delay_duration = (end_time - start_time) * 1000  # 转换为毫秒
        if delay_duration < 3000:
            return delay_duration, None
        else:
            print(f"节点 {node} 的延迟过高: {delay_duration}ms")
            return delay_duration, None
    except requests.RequestException as e:
        print(f"延迟测试节点 {node} 时发生错误: {e}")
        return None, str(e)

def test_url(node):
    url = extract_host_from_node(node)
    if url:
        try:
            start_time = time.time()
            response = requests.get(url_test_url, timeout=10)
            response.raise_for_status()
            end_time = time.time()
            url_test_duration = (end_time - start_time) * 1000  # 转换为毫秒
            return url_test_duration
        except requests.RequestException as e:
            print(f"节点 {node} 的 URL 测试失败: {e}")
            return None
    return None

def test_node_download_speed(node):
    try:
        start_time = time.time()
        response = requests.get(download_test_url, timeout=10, stream=True)
        response.raise_for_status()
        end_time = time.time()
        download_duration = end_time - start_time
        if download_duration < 30:
            content_length = int(response.headers.get('content-length', 0))
            speed = (content_length / 1024 / 1024) / download_duration
            return speed
        else:
            print(f"节点 {node} 的下载速度过慢: {download_duration}秒")
            return None
    except requests.RequestException as e:
        print(f"下载测试节点 {node} 时发生错误: {e}")
        return None

def process_nodes_from_url(url):
    valid_nodes = []
    nodes = fetch_nodes(url)
    for node in nodes:
        print(f"原始节点: {node}")  # 调试输出
        if is_node_valid(node):
            delay, delay_error = test_node_delay(node)
            if delay is None:
                continue
            url_test_duration = test_url(node)
            if url_test_duration is None:
                continue
            download_speed = test_node_download_speed(node)
            if download_speed is None:
                continue

            region = get_node_region(node)
            valid_nodes.append(NodeResult(node, delay, url_test_duration, download_speed, region))
    return valid_nodes

def is_node_valid(node):
    host = extract_host_from_node(node)
    if host is None:
        return False
    try:
        socket.gethostbyname(host)
        return True
    except (socket.error, UnicodeError) as e:
        print(f"节点 {node} 无法解析主机名或连接失败: {e}")
        return False

def get_node_name(node):
    if node.startswith('vmess://'):
        try:
            decoded = base64.b64decode(node[8:]).decode('utf-8')
            data = json.loads(decoded)
            return data.get('ps', 'unknown')
        except Exception as e:
            print(f"解析 vmess 节点名称时发生错误: {e}")
            return 'unknown'
    elif node.startswith('trojan://'):
        return extract_host_from_node(node)  # 保持原始名称
    elif node.startswith('hysteria://') or node.startswith('hysteria2://'):
        return node.split('#', 1)[1] if '#' in node else 'unknown'
    elif node.startswith('shadowsocks://'):
        return node.split(':', 1)[1] if ':' in node else 'unknown'
    else:
        return 'unknown'

def get_node_region(node):
    host = extract_host_from_node(node)
    if host:
        try:
            response = requests.get(f'{region_lookup_url}{host}', timeout=10)
            response.raise_for_status()
            data = response.json()
            return f"🚩{data.get('countryCode', 'XX')}"
        except requests.RequestException as e:
            print(f"获取节点 {node} 区域时发生错误: {e}")
            return '🚩XX'
    return '🚩XX'

def format_node_name(node, delay, url_test, download_speed, region):
    node_type = get_node_type(node)
    formatted_speed = f"{download_speed:.2f}M"
    base_part = node.split('://', 1)[0] + '://'  # 保留协议前缀
    address_part = node.split('://', 1)[1]  # 保留节点信息
    return f"{base_part}{address_part.split('#', 1)[0]}#{region} | 🟢 | {node_type} | {formatted_speed}"

def get_node_type(node):
    if node.startswith('vmess://'):
        return 'vmess'
    elif node.startswith('trojan://'):
        return 'trojan'
    elif node.startswith('hysteria://'):
        return 'hysteria'
    elif node.startswith('hysteria2://'):
        return 'hysteria2'
    elif node.startswith('shadowsocks://'):
        return 'shadowsocks'
    else:
        return 'other'

def deduplicate_nodes(nodes):
    seen_keys = set()
    deduplicated_nodes = []
    for node in nodes:
        key = extract_key_from_node(node.node)
        if key and key not in seen_keys:
            seen_keys.add(key)
            deduplicated_nodes.append(node)
    return deduplicated_nodes

all_valid_nodes = []

for url in node_urls:
    print(f"正在处理 URL: {url}")
    valid_nodes = process_nodes_from_url(url)
    if valid_nodes:
        all_valid_nodes.extend(valid_nodes)
    else:
        print(f"URL {url} 未找到有效节点")

# Deduplicate nodes
deduplicated_nodes = deduplicate_nodes(all_valid_nodes)

# Format each node and retain other details
formatted_nodes = [
    NodeResult(
        format_node_name(node.node, node.delay, node.url_test, node.download_speed, node.region),
        node.delay,
        node.url_test,
        node.download_speed,
        node.region
    )
    for node in deduplicated_nodes
]

unique_nodes = list(set(node.node for node in formatted_nodes))
sorted_nodes = sorted(unique_nodes, key=get_node_type)

if sorted_nodes:
    encoded_nodes = base64.b64encode('\n'.join(sorted_nodes).encode('utf-8')).decode('utf-8')
    with open('abc.txt', 'w') as f:
        f.write(encoded_nodes)
    print("有效节点已成功写入 abc.txt")
else:
    print("未找到有效节点。文件 abc.txt 将为空。")
