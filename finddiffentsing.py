import os
import re
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from collections import defaultdict
from datetime import datetime

def deep_clean_text(text):
    """深度清理文本"""
    if not text:
        return ""
    
    # 转换为小写
    text = str(text).lower().strip()
    
    # 移除各种括号及其内容
    text = re.sub(r'[\(\[].*?[\)\]]', '', text)
    
    # 移除常见版本标记
    version_markers = ['live', 'ver.', 'version', 'remix', 'acoustic', 
                      'instrumental', 'demo', 'edit', 'mix', 'feat.', 'ft.']
    for marker in version_markers:
        text = re.sub(rf'\b{marker}\b', '', text)
    
    # 移除特殊字符，保留字母、数字、中文和空格
    text = re.sub(r'[^\w\u4e00-\u9fff\s]', ' ', text)
    
    # 合并多个空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_artist_title_comprehensive(filepath, filename):
    """综合提取歌手和歌名，使用多种策略"""
    strategies = []
    
    # 策略1: 使用音频元数据
    try:
        if filepath.lower().endswith('.mp3'):
            audio = EasyID3(filepath)
            artist = audio.get('artist', [None])[0]
            title = audio.get('title', [None])[0]
        elif filepath.lower().endswith('.flac'):
            audio = FLAC(filepath)
            artist = audio.get('artist', [None])[0]
            title = audio.get('title', [None])[0]
        else:
            artist, title = None, None
        
        if artist and title:
            strategies.append(('metadata', artist, title))
    except:
        pass
    
    # 策略2: 从文件名解析 (歌手-歌名 格式)
    name_no_ext = os.path.splitext(filename)[0]
    
    # 尝试不同分隔符
    separators = [' - ', ' — ', ' – ', '-', '_', '~']
    
    for sep in separators:
        if sep in name_no_ext:
            parts = name_no_ext.split(sep, 1)
            if len(parts) == 2:
                artist, title = parts[0].strip(), parts[1].strip()
                if artist and title:
                    strategies.append((f'filename{sep}', artist, title))
    
    # 策略3: 尝试反转 (歌名-歌手 格式)
    # 这通常发生在中文歌曲中
    if ' - ' in name_no_ext or '-' in name_no_ext:
        for sep in [' - ', '-']:
            if sep in name_no_ext:
                parts = name_no_ext.split(sep, 1)
                if len(parts) == 2:
                    # 假设第二部分是歌手
                    title, artist = parts[0].strip(), parts[1].strip()
                    if artist and title:
                        # 检查第二部分是否看起来像歌手（较短，常见歌手名）
                        if len(artist) <= 15:  # 歌手名通常不会太长
                            strategies.append((f'filename_rev{sep}', artist, title))
    
    # 策略4: 使用正则表达式匹配常见模式
    patterns = [
        (r'^(.+?)[\s\-_]+(.+)$', 'artist-title'),  # 任意分隔符
        (r'^(.+?)[\s\-_]+by[\s\-_]+(.+)$', 'title-artist'),  # ... by ...
        (r'^(.+?)[\s\-_]+ft\.?[\s\-_]+(.+)$', 'artist-feat'),  # ... ft. ...
    ]
    
    for pattern, pattern_type in patterns:
        match = re.match(pattern, name_no_ext)
        if match:
            if pattern_type == 'artist-title':
                artist, title = match.group(1), match.group(2)
            elif pattern_type == 'title-artist':
                title, artist = match.group(1), match.group(2)
            else:
                artist, title = match.group(1), match.group(2)
            
            if artist and title:
                strategies.append((f'regex_{pattern_type}', artist.strip(), title.strip()))
    
    # 清理所有策略的结果
    cleaned_strategies = []
    for strategy_name, artist, title in strategies:
        clean_artist = deep_clean_text(artist)
        clean_title = deep_clean_text(title)
        if clean_artist and clean_title:
            cleaned_strategies.append((strategy_name, clean_artist, clean_title))
    
    return cleaned_strategies

def build_smart_index(folder_path, folder_name):
    """构建智能索引，记录每个文件的所有可能匹配方式"""
    print(f"\n📁 正在分析{folder_name}...")
    
    file_index = {}  # 文件名 -> 所有可能的(歌手, 歌名)组合
    strategy_counts = defaultdict(int)
    
    total_files = 0
    audio_files = 0
    
    for filename in os.listdir(folder_path):
        total_files += 1
        filepath = os.path.join(folder_path, filename)
        
        if not os.path.isfile(filepath):
            continue
            
        if not filename.lower().endswith(('.mp3', '.flac')):
            continue
            
        audio_files += 1
        
        # 获取所有可能的歌手-歌名组合
        strategies = extract_artist_title_comprehensive(filepath, filename)
        
        if strategies:
            file_index[filename] = strategies
            for strategy, _, _ in strategies:
                strategy_counts[strategy] += 1
        else:
            print(f"  ⚠️  无法解析: {filename}")
    
    print(f"  音频文件: {audio_files}/{total_files}")
    print(f"  成功解析: {len(file_index)} 个文件")
    print(f"  解析策略使用情况:")
    for strategy, count in strategy_counts.items():
        print(f"    {strategy}: {count}")
    
    # 构建反向索引: (歌手, 歌名) -> [文件名列表]
    reverse_index = defaultdict(list)
    for filename, strategies in file_index.items():
        for _, artist, title in strategies:
            key = (artist, title)
            reverse_index[key].append(filename)
    
    return file_index, reverse_index

def find_unique_with_cross_check(folder1, folder2):
    """使用交叉检查找出独特歌曲"""
    
    print("=" * 80)
    print("🎵 智能歌曲匹配系统 - 交叉验证模式")
    print("=" * 80)
    
    # 构建两个文件夹的索引
    index1, reverse1 = build_smart_index(folder1, "第一个文件夹（FLAC）")
    index2, reverse2 = build_smart_index(folder2, "第二个文件夹（MP3）")
    
    print("\n" + "=" * 80)
    print("🔍 开始交叉验证匹配...")
    print("=" * 80)
    
    # 找出第二个文件夹中的独特歌曲
    unique_songs = []
    match_details = []
    
    for filename2, strategies2 in index2.items():
        matched = False
        best_match = None
        best_similarity = 0
        
        # 检查每个可能的(歌手, 歌名)组合
        for strategy2, artist2, title2 in strategies2:
            key2 = (artist2, title2)
            
            # 直接匹配
            if key2 in reverse1:
                matched = True
                matched_files = reverse1[key2]
                match_details.append((filename2, "精确匹配", strategy2, matched_files[0]))
                break
            
            # 如果没有直接匹配，尝试相似度匹配
            for key1 in reverse1.keys():
                artist1, title1 = key1
                
                # 计算歌手相似度
                artist_sim = calculate_similarity(artist1, artist2)
                
                # 如果歌手高度相似，检查歌名
                if artist_sim > 0.8:
                    title_sim = calculate_similarity(title1, title2)
                    overall_sim = (artist_sim + title_sim) / 2
                    
                    if overall_sim > best_similarity:
                        best_similarity = overall_sim
                        best_match = (artist1, title1, overall_sim)
        
        # 如果找到相似匹配且相似度足够高
        if not matched and best_match and best_similarity > 0.85:
            matched = True
            artist1, title1, similarity = best_match
            match_details.append((filename2, f"模糊匹配({similarity:.1%})", f"{artist2}-{title2}", f"{artist1}-{title1}"))
        
        # 如果没有匹配，则认为是独特歌曲
        if not matched:
            unique_songs.append(filename2)
    
    # 输出匹配统计
    print(f"\n📊 匹配统计:")
    print(f"  第二个文件夹总歌曲数: {len(index2)}")
    print(f"  已匹配歌曲数: {len(match_details)}")
    print(f"  独特歌曲数: {len(unique_songs)}")
    
    # 显示匹配详情（前10个）
    if match_details:
        print(f"\n🔗 匹配示例（前10个）:")
        for i, (file2, match_type, info2, info1) in enumerate(match_details[:10], 1):
            print(f"  {i:2d}. {file2}")
            print(f"     {match_type}: {info2} → {info1}")
    
    return unique_songs, match_details, len(index1), len(index2)

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度（0-1）"""
    if not str1 or not str2:
        return 0
    
    # 如果完全相同
    if str1 == str2:
        return 1.0
    
    # 计算编辑距离相似度
    len1, len2 = len(str1), len(str2)
    max_len = max(len1, len2)
    
    if max_len == 0:
        return 1.0
    
    # 计算Levenshtein距离
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    distance = levenshtein_distance(str1, str2)
    similarity = 1.0 - (distance / max_len)
    
    return similarity

def manual_verification(folder1, folder2, unique_songs, sample_size=20):
    """手动验证样本"""
    print("\n" + "=" * 80)
    print("🔎 手动验证样本")
    print("=" * 80)
    
    if not unique_songs:
        print("没有独特歌曲需要验证")
        return
    
    # 随机选择样本（为了可重现，选择前n个）
    sample = unique_songs[:min(sample_size, len(unique_songs))]
    
    print(f"\n随机选择 {len(sample)} 个样本进行验证:")
    print("-" * 80)
    
    verification_results = []
    
    for i, filename in enumerate(sample, 1):
        print(f"\n{i:2d}. 文件: {filename}")
        
        # 显示文件信息
        filepath2 = os.path.join(folder2, filename)
        
        # 尝试显示元数据
        try:
            if filename.lower().endswith('.mp3'):
                audio = EasyID3(filepath2)
                artist = audio.get('artist', [None])[0]
                title = audio.get('title', [None])[0]
            elif filename.lower().endswith('.flac'):
                audio = FLAC(filepath2)
                artist = audio.get('artist', [None])[0]
                title = audio.get('title', [None])[0]
            else:
                artist, title = None, None
            
            if artist and title:
                print(f"    元数据: {artist} - {title}")
            else:
                print(f"    无法读取元数据")
        except:
            print(f"    无法读取元数据")
        
        # 询问用户是否确认这是独特歌曲
        response = input(f"    这个文件在第一个文件夹中有对应版本吗？(y=有, n=没有, s=跳过): ").strip().lower()
        
        if response == 'y':
            verification_results.append((filename, False))  # 误判
            print(f"    → 标记为误判")
        elif response == 'n':
            verification_results.append((filename, True))   # 正确
            print(f"    → 确认独特")
        else:
            verification_results.append((filename, None))   # 跳过
            print(f"    → 跳过")
    
    # 统计验证结果
    total_checked = len(verification_results)
    correct = sum(1 for _, is_correct in verification_results if is_correct is True)
    incorrect = sum(1 for _, is_correct in verification_results if is_correct is False)
    skipped = total_checked - correct - incorrect
    
    accuracy = correct / total_checked * 100 if total_checked > 0 else 0
    
    print(f"\n📈 验证结果:")
    print(f"  检查样本: {total_checked} 个")
    print(f"  确认独特: {correct} 个")
    print(f"  误判: {incorrect} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  准确率: {accuracy:.1f}%")
    
    # 根据准确率调整独特歌曲数量估计
    if total_checked > 0 and correct + incorrect > 0:
        actual_rate = correct / (correct + incorrect)
        estimated_correct = len(unique_songs) * actual_rate
        print(f"\n📊 根据样本估计:")
        print(f"  当前独特歌曲数: {len(unique_songs)}")
        print(f"  估计真正独特: {estimated_correct:.0f} 个")
    
    return verification_results

def main_smart():
    """主函数 - 智能匹配版本"""
    print("🎵 智能歌曲匹配系统 v3.0")
    print("=" * 80)
    print("特点:")
    print("• 多策略解析（元数据 + 多种文件名格式）")
    print("• 交叉验证匹配")
    print("• 支持模糊匹配")
    print("• 提供手动验证样本")
    print("=" * 80)
    
    # 获取文件夹路径
    print("\n📂 请输入文件夹路径:")
    folder1 = input("第一个文件夹（FLAC文件）: ").strip('"').strip()
    folder2 = input("第二个文件夹（MP3文件）: ").strip('"').strip()
    
    if not os.path.exists(folder1):
        print(f"\n❌ 错误: 第一个文件夹不存在")
        return
    if not os.path.exists(folder2):
        print(f"\n❌ 错误: 第二个文件夹不存在")
        return
    
    # 执行智能匹配
    unique_songs, match_details, total1, total2 = find_unique_with_cross_check(folder1, folder2)
    
    # 保存结果
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存独特歌曲列表
    unique_file = os.path.join(desktop, f"独特歌曲_智能匹配_{timestamp}.txt")
    with open(unique_file, 'w', encoding='utf-8') as f:
        f.write("智能匹配 - 独特歌曲列表\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"第一个文件夹: {folder1}\n")
        f.write(f"  歌曲数: {total1}\n")
        f.write(f"第二个文件夹: {folder2}\n")
        f.write(f"  歌曲数: {total2}\n\n")
        f.write(f"独特歌曲数量: {len(unique_songs)}\n\n")
        f.write("独特歌曲列表:\n")
        f.write("-" * 60 + "\n")
        
        for i, song in enumerate(unique_songs, 1):
            f.write(f"{i:3d}. {song}\n")
    
    # 保存匹配详情
    if match_details:
        match_file = os.path.join(desktop, f"匹配详情_{timestamp}.txt")
        with open(match_file, 'w', encoding='utf-8') as f:
            f.write("匹配详情报告\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"匹配总数: {len(match_details)}\n\n")
            
            for i, (file2, match_type, info2, info1) in enumerate(match_details, 1):
                f.write(f"{i:3d}. {file2}\n")
                f.write(f"    类型: {match_type}\n")
                f.write(f"    匹配: {info2} → {info1}\n\n")
    
    print(f"\n💾 结果已保存:")
    print(f"  独特歌曲列表: {unique_file}")
    if match_details:
        print(f"  匹配详情: {match_file}")
    
    # 提供手动验证选项
    verify = input("\n是否手动验证样本？(y/n): ").strip().lower()
    if verify == 'y':
        manual_verification(folder1, folder2, unique_songs)
    
    print(f"\n✅ 操作完成！")
    input("按Enter键退出...")

def quick_analysis(folder1, folder2):
    """快速分析工具，显示关键信息"""
    print("\n🔍 快速分析模式...")
    
    # 收集两个文件夹的文件名
    files1 = [f for f in os.listdir(folder1) if f.lower().endswith(('.mp3', '.flac'))]
    files2 = [f for f in os.listdir(folder2) if f.lower().endswith(('.mp3', '.flac'))]
    
    print(f"第一个文件夹: {len(files1)} 个音频文件")
    print(f"第二个文件夹: {len(files2)} 个音频文件")
    
    # 分析命名模式
    print("\n📊 文件名模式分析:")
    
    patterns1 = analyze_naming_patterns(files1)
    patterns2 = analyze_naming_patterns(files2)
    
    print(f"第一个文件夹模式:")
    for pattern, count in patterns1.most_common(5):
        print(f"  {pattern}: {count} 个 ({count/len(files1)*100:.1f}%)")
    
    print(f"第二个文件夹模式:")
    for pattern, count in patterns2.most_common(5):
        print(f"  {pattern}: {count} 个 ({count/len(files2)*100:.1f}%)")
    
    # 简单匹配测试
    print("\n🧪 简单匹配测试:")
    simple_matches = 0
    for file2 in files2[:20]:  # 测试前20个
        name2_no_ext = os.path.splitext(file2)[0].lower()
        found = False
        
        for file1 in files1:
            name1_no_ext = os.path.splitext(file1)[0].lower()
            # 检查是否有明显的重叠
            if name1_no_ext in name2_no_ext or name2_no_ext in name1_no_ext:
                found = True
                break
        
        if found:
            simple_matches += 1
    
    print(f"  前20个文件中，{simple_matches} 个有简单匹配")
    
    return len(files1), len(files2)

def analyze_naming_patterns(filenames):
    """分析文件名模式"""
    from collections import Counter
    
    patterns = Counter()
    
    for filename in filenames:
        name = os.path.splitext(filename)[0]
        
        if ' - ' in name:
            patterns['" - " 分隔'] += 1
        elif '-' in name:
            patterns['"-" 分隔'] += 1
        elif '_' in name:
            patterns['"_" 分隔'] += 1
        elif ' ' in name:
            patterns['空格分隔'] += 1
        elif any(char in name for char in ['·', '•', '・']):
            patterns['特殊字符分隔'] += 1
        elif re.search(r'[\u4e00-\u9fff].*[\u4e00-\u9fff]', name):
            patterns['纯中文无分隔'] += 1
        else:
            patterns['其他格式'] += 1
    
    return patterns

if __name__ == "__main__":
    print("🎵 歌曲匹配工具集")
    print("=" * 60)
    print("1. 智能匹配系统（推荐）")
    print("2. 快速分析模式")
    print("3. 退出")
    
    choice = input("\n请选择模式 (1/2/3): ").strip()
    
    if choice == '1':
        main_smart()
    elif choice == '2':
        folder1 = input("第一个文件夹路径: ").strip('"').strip()
        folder2 = input("第二个文件夹路径: ").strip('"').strip()
        
        if os.path.exists(folder1) and os.path.exists(folder2):
            quick_analysis(folder1, folder2)
            input("\n按Enter键退出...")
        else:
            print("❌ 文件夹不存在")
    elif choice == '3':
        print("退出程序")
    else:
        print("❌ 无效选择")