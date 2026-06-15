"""
CineLog UI 自动化测试
使用 Selenium + pytest
基于实际前端代码结构编写，所有选择器均来自真实DOM
"""

import os
import time
import pytest
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
)

# ========== 配置 ==========
# 截图保存目录
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
# 前端文件路径
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend"
)
INDEX_URL = f"file:///{FRONTEND_DIR.replace(os.sep, '/')}/index.html"
LOGIN_URL = f"file:///{FRONTEND_DIR.replace(os.sep, '/')}/login.html"

# 测试用户
TEST_USERNAME = "testuser_cinelog"
TEST_PASSWORD = "test123"


def ensure_screenshots_dir():
    """确保截图目录存在"""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def take_screenshot(driver, name):
    """截图并保存到 tests/screenshots/"""
    ensure_screenshots_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(filepath)
    print(f"[截图] 已保存: {filepath}")
    return filepath


def safe_find_element(driver, by, value, timeout=5):
    """
    安全查找元素，找不到时输出明确日志而不是直接崩溃
    返回元素或 None
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        print(f"[警告] 元素未找到: {by}='{value}' (等待{timeout}秒超时)")
        return None


def safe_find_elements(driver, by, value, timeout=5):
    """安全查找多个元素"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return driver.find_elements(by, value)
    except (TimeoutException, NoSuchElementException):
        print(f"[警告] 元素组未找到: {by}='{value}' (等待{timeout}秒超时)")
        return []


# ========== Fixtures ==========


@pytest.fixture(scope="session")
def driver():
    """创建 WebDriver 实例（整个测试会话共用）"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=480,900")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-file-access-from-files")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)

    yield driver
    driver.quit()


@pytest.fixture(scope="session", autouse=True)
def setup_login(driver):
    """
    测试前先完成注册/登录，设置 localStorage
    确保主页能正常加载（不会被重定向到login.html）
    """
    # 先访问登录页进行注册
    driver.get(LOGIN_URL)
    time.sleep(1)

    # 在 localStorage 中注入用户信息，绕过登录跳转
    # 根据 login.html 源码，需要设置 cinelog_user 和 cinelog_token
    driver.execute_script(
        """
        // 注册用户到 cinelog_users
        var users = JSON.parse(localStorage.getItem('cinelog_users') || '{}');
        users[arguments[0]] = {
            password: arguments[1],
            joinDate: new Date().toLocaleDateString('zh-CN')
        };
        localStorage.setItem('cinelog_users', JSON.stringify(users));
        
        // 设置当前登录状态
        localStorage.setItem('cinelog_user', JSON.stringify({
            username: arguments[0],
            joinDate: new Date().toLocaleDateString('zh-CN')
        }));
        localStorage.setItem('cinelog_token', 'local_' + arguments[0]);
    """,
        TEST_USERNAME,
        TEST_PASSWORD,
    )

    # 导航到主页
    driver.get(INDEX_URL)
    time.sleep(2)

    yield


# ========== 测试用例 ==========


class TestHomePage:
    """首页测试"""

    def test_home_page_loads(self, driver):
        """检查首页加载成功"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 检查 pageHome 是否存在且有 active 类
        page_home = safe_find_element(driver, By.ID, "pageHome")
        assert page_home is not None, "首页元素 #pageHome 不存在"

        # 检查 page 是否 active
        classes = page_home.get_attribute("class")
        assert "active" in classes, f"首页未激活，当前class: {classes}"

        take_screenshot(driver, "test_home_page_loads")
        print("[通过] 首页加载成功")

    def test_home_title_display(self, driver):
        """检查「我的光影手账」是否显示"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 标题在 .cover-title h1 中
        title_el = safe_find_element(driver, By.CSS_SELECTOR, ".cover-title h1")
        assert title_el is not None, "封面标题元素 .cover-title h1 不存在"

        title_text = title_el.text
        assert "我的光影手账" in title_text, f"标题文字不正确，实际为: {title_text}"

        take_screenshot(driver, "test_home_title_display")
        print(f"[通过] 标题显示正确: {title_text}")

    def test_home_stats_section(self, driver):
        """检查首页统计便签区域是否存在"""
        driver.get(INDEX_URL)
        time.sleep(2)

        stats = safe_find_element(driver, By.CSS_SELECTOR, ".stats-sticky-notes")
        assert stats is not None, "统计便签区域 .stats-sticky-notes 不存在"

        # 检查4个统计项
        stat_total = safe_find_element(driver, By.ID, "statTotalHome")
        stat_month = safe_find_element(driver, By.ID, "statMonthHome")
        stat_streak = safe_find_element(driver, By.ID, "statStreakHome")
        stat_mood = safe_find_element(driver, By.ID, "statMoodHome")

        assert stat_total is not None, "总记录统计 #statTotalHome 不存在"
        assert stat_month is not None, "本月统计 #statMonthHome 不存在"
        assert stat_streak is not None, "连续天数统计 #statStreakHome 不存在"
        assert stat_mood is not None, "本月心情统计 #statMoodHome 不存在"

        take_screenshot(driver, "test_home_stats_section")
        print("[通过] 首页统计便签区域正常")

    def test_home_greeting(self, driver):
        """检查问候语区域"""
        driver.get(INDEX_URL)
        time.sleep(2)

        greeting = safe_find_element(driver, By.ID, "greetingTime")
        assert greeting is not None, "问候语元素 #greetingTime 不存在"
        assert greeting.text != "", "问候语文本为空"

        take_screenshot(driver, "test_home_greeting")
        print(f"[通过] 问候语显示: {greeting.text}")


class TestTabNavigation:
    """底部导航Tab切换测试"""

    @pytest.mark.parametrize(
        "page_name,page_id,tab_label",
        [
            ("Home", "pageHome", "首页"),
            ("Records", "pageRecords", "记录"),
            ("Calendar", "pageCalendar", "月历"),
            ("Analytics", "pageAnalytics", "数据"),
            ("Favorites", "pageFavorites", "收藏"),
            ("Profile", "pageProfile", "我的"),
        ],
    )
    def test_tab_navigation(self, driver, page_name, page_id, tab_label):
        """依次测试所有Tab切换"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 找到对应的tab按钮，通过 data-page 属性定位
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, f'.tab-item[data-page="{page_name}"]'
        )
        assert tab_btn is not None, f"Tab按钮 data-page='{page_name}' 不存在"

        # 点击tab
        tab_btn.click()
        time.sleep(1)

        # 验证页面切换
        page_el = safe_find_element(driver, By.ID, page_id)
        assert page_el is not None, f"页面元素 #{page_id} 不存在"

        # 检查页面是否显示（active类 或 display不为none）
        is_displayed = page_el.is_displayed()
        assert is_displayed, f"页面 #{page_id} 未显示"

        # 检查tab按钮是否active
        tab_classes = tab_btn.get_attribute("class")
        assert "active" in tab_classes, f"Tab按钮未激活，class: {tab_classes}"

        take_screenshot(driver, f"test_tab_{page_name}")
        print(f"[通过] Tab切换成功: {tab_label} -> #{page_id}")


class TestAnalyticsPage:
    """数据分析页测试"""

    def test_growth_tree_section(self, driver):
        """检查成长树组件是否成功渲染"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到数据页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Analytics"]'
        )
        assert tab_btn is not None, "数据Tab按钮不存在"
        tab_btn.click()
        time.sleep(1)

        # 检查成长树区域
        growth_tree_section = safe_find_element(
            driver, By.CSS_SELECTOR, ".growth-tree-section"
        )
        assert growth_tree_section is not None, "成长树区域 .growth-tree-section 不存在"

        # 检查成长树画布
        growth_tree_canvas = safe_find_element(driver, By.ID, "growthTreeCanvas")
        assert growth_tree_canvas is not None, "成长树画布 #growthTreeCanvas 不存在"

        # 检查成长树内容是否渲染（应该有内容）
        canvas_html = growth_tree_canvas.get_attribute("innerHTML")
        assert len(canvas_html) > 0, "成长树画布内容为空，未渲染"

        take_screenshot(driver, "test_growth_tree")
        print("[通过] 成长树组件渲染成功")

    def test_wishing_jars_section(self, driver):
        """检查星星许愿瓶（评分统计）组件是否成功渲染"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到数据页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Analytics"]'
        )
        assert tab_btn is not None, "数据Tab按钮不存在"
        tab_btn.click()
        time.sleep(1)

        # 检查许愿瓶区域
        wishing_section = safe_find_element(
            driver, By.CSS_SELECTOR, ".wishing-jar-section"
        )
        assert wishing_section is not None, "许愿瓶区域 .wishing-jar-section 不存在"

        # 检查许愿瓶容器
        wishing_jars = safe_find_element(driver, By.ID, "wishingJars")
        assert wishing_jars is not None, "许愿瓶容器 #wishingJars 不存在"

        # 检查是否有瓶子渲染
        jars = safe_find_elements(
            driver, By.CSS_SELECTOR, "#wishingJars .wishing-jar"
        )
        assert len(jars) > 0, "评分统计许愿瓶未渲染"

        take_screenshot(driver, "test_wishing_jars")
        print(f"[通过] 评分统计组件渲染成功，共{len(jars)}个许愿瓶")

    def test_annual_report(self, driver):
        """检查年度观影报告"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到数据页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Analytics"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 检查年度报告区域
        report = safe_find_element(driver, By.ID, "annualReport")
        assert report is not None, "年度报告 #annualReport 不存在"

        # 检查报告各项
        report_total = safe_find_element(driver, By.ID, "reportTotal")
        report_fav_type = safe_find_element(driver, By.ID, "reportFavType")
        report_avg_rating = safe_find_element(driver, By.ID, "reportAvgRating")
        report_high_month = safe_find_element(driver, By.ID, "reportHighMonth")

        assert report_total is not None, "#reportTotal 不存在"
        assert report_fav_type is not None, "#reportFavType 不存在"
        assert report_avg_rating is not None, "#reportAvgRating 不存在"
        assert report_high_month is not None, "#reportHighMonth 不存在"

        take_screenshot(driver, "test_annual_report")
        print("[通过] 年度观影报告渲染成功")


class TestFavoritesPage:
    """收藏页测试"""

    def test_favorites_page_structure(self, driver):
        """检查收藏页结构是否正常"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到收藏页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Favorites"]'
        )
        assert tab_btn is not None, "收藏Tab按钮不存在"
        tab_btn.click()
        time.sleep(1)

        # 收藏页应该存在收藏墙或空状态
        collage_wall = safe_find_element(driver, By.ID, "collageWall")
        empty_favorites = safe_find_element(driver, By.ID, "emptyFavorites")

        assert (
            collage_wall is not None or empty_favorites is not None
        ), "收藏墙 #collageWall 和空状态 #emptyFavorites 都不存在"

        # 检查是否有收藏卡片（5星自动收藏）
        # mock数据中有多个5星记录，应该有卡片
        collage_items = safe_find_elements(
            driver, By.CSS_SELECTOR, "#collageWall .collage-item"
        )

        if len(collage_items) > 0:
            print(f"[通过] 收藏墙有 {len(collage_items)} 个收藏卡片")
            # 验证收藏卡片内容
            first_item = collage_items[0]
            title_el = first_item.find_elements(By.CSS_SELECTOR, ".collage-title")
            assert len(title_el) > 0, "收藏卡片缺少标题 .collage-title"
        else:
            # 空状态也可以接受
            if empty_favorites and empty_favorites.is_displayed():
                print("[通过] 收藏页显示空状态（无5星记录）")
            else:
                print("[警告] 收藏页既无卡片也无空状态提示")

        take_screenshot(driver, "test_favorites_page")

    def test_favorites_card_content(self, driver):
        """检查收藏卡片显示内容"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到收藏页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Favorites"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 查找收藏卡片
        collage_items = safe_find_elements(
            driver, By.CSS_SELECTOR, "#collageWall .collage-item"
        )

        if len(collage_items) > 0:
            item = collage_items[0]
            # 验证卡片结构
            photo = item.find_elements(By.CSS_SELECTOR, ".collage-photo")
            title = item.find_elements(By.CSS_SELECTOR, ".collage-title")
            rating = item.find_elements(By.CSS_SELECTOR, ".collage-rating")

            assert len(photo) > 0, "收藏卡片缺少图片区域 .collage-photo"
            assert len(title) > 0, "收藏卡片缺少标题 .collage-title"
            assert len(rating) > 0, "收藏卡片缺少评分 .collage-rating"

            take_screenshot(driver, "test_favorites_card_content")
            print(f"[通过] 收藏卡片内容结构完整: {title[0].text}")
        else:
            pytest.skip("无收藏卡片，跳过内容检查")


class TestProfilePage:
    """个人页（我的）测试"""

    def test_keyword_section_exists(self, driver):
        """检查年度关键词区域是否存在"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到我的页面
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Profile"]'
        )
        assert tab_btn is not None, "我的Tab按钮不存在"
        tab_btn.click()
        time.sleep(1)

        # 检查年度关键词区域
        keywords_section = safe_find_element(
            driver, By.CSS_SELECTOR, ".passport-keywords"
        )
        assert keywords_section is not None, "年度关键词区域 .passport-keywords 不存在"

        # 检查关键词云容器
        keyword_cloud = safe_find_element(driver, By.ID, "keywordCloud")
        assert keyword_cloud is not None, "关键词云 #keywordCloud 不存在"

        # 检查标题
        keyword_title = keywords_section.find_elements(By.TAG_NAME, "h3")
        assert len(keyword_title) > 0, "关键词区域缺少标题"
        assert "年度关键词" in keyword_title[0].text, (
            f"关键词标题不正确: {keyword_title[0].text}"
        )

        take_screenshot(driver, "test_profile_keywords")
        print("[通过] 年度关键词区域存在")

    def test_profile_info(self, driver):
        """检查个人信息展示"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到我的页面
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Profile"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 检查用户名
        profile_name = safe_find_element(driver, By.ID, "profileName")
        assert profile_name is not None, "#profileName 不存在"
        assert profile_name.text != "", "用户名为空"

        # 检查统计信息
        profile_total = safe_find_element(driver, By.ID, "profileTotal")
        assert profile_total is not None, "#profileTotal 不存在"

        # 检查徽章区域
        badges_grid = safe_find_element(driver, By.ID, "badgesGrid")
        assert badges_grid is not None, "#badgesGrid 不存在"

        take_screenshot(driver, "test_profile_info")
        print(f"[通过] 个人页信息显示正常，用户名: {profile_name.text}")


class TestRecordsPage:
    """记录页测试"""

    def test_records_page_loads(self, driver):
        """检查记录页加载"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        assert tab_btn is not None, "记录Tab按钮不存在"
        tab_btn.click()
        time.sleep(1)

        # 检查页面
        page_records = safe_find_element(driver, By.ID, "pageRecords")
        assert page_records is not None, "#pageRecords 不存在"
        assert page_records.is_displayed(), "记录页未显示"

        # 检查时间线容器
        timeline = safe_find_element(driver, By.ID, "recordsTimeline")
        assert timeline is not None, "#recordsTimeline 不存在"

        take_screenshot(driver, "test_records_page")
        print("[通过] 记录页加载成功")

    def test_add_record_button_exists(self, driver):
        """检查新增记录按钮存在"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 查找"写新的"按钮（class为 btn-handwrite）
        add_btn = safe_find_element(driver, By.CSS_SELECTOR, ".btn-handwrite")
        assert add_btn is not None, "新增记录按钮 .btn-handwrite 不存在"
        assert "写新的" in add_btn.text, f"按钮文字不正确: {add_btn.text}"

        take_screenshot(driver, "test_add_record_button")
        print(f"[通过] 新增记录按钮存在: {add_btn.text}")

    def test_open_add_modal(self, driver):
        """检查点击新增按钮弹出添加记录弹窗"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 点击新增按钮
        add_btn = safe_find_element(driver, By.CSS_SELECTOR, ".btn-handwrite")
        assert add_btn is not None, "新增记录按钮不存在"
        add_btn.click()
        time.sleep(0.5)

        # 验证弹窗显示
        add_modal = safe_find_element(driver, By.ID, "addModal")
        assert add_modal is not None, "添加记录弹窗 #addModal 不存在"

        modal_classes = add_modal.get_attribute("class")
        assert "active" in modal_classes, f"弹窗未激活，class: {modal_classes}"

        # 检查弹窗内的表单元素
        title_input = safe_find_element(driver, By.ID, "recordTitle")
        type_select = safe_find_element(driver, By.ID, "recordType")
        date_input = safe_find_element(driver, By.ID, "recordDate")
        comment_textarea = safe_find_element(driver, By.ID, "recordComment")

        assert title_input is not None, "名称输入框 #recordTitle 不存在"
        assert type_select is not None, "类型选择 #recordType 不存在"
        assert date_input is not None, "日期输入 #recordDate 不存在"
        assert comment_textarea is not None, "短评输入 #recordComment 不存在"

        # 检查日期是否自动填充为今天
        date_value = date_input.get_attribute("value")
        today = datetime.now().strftime("%Y-%m-%d")
        assert date_value == today, f"日期未自动填充，期望{today}，实际{date_value}"

        take_screenshot(driver, "test_add_modal_open")
        print("[通过] 添加记录弹窗正常打开，表单元素完整")

    def test_close_add_modal(self, driver):
        """检查关闭添加记录弹窗"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页并打开弹窗
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        tab_btn.click()
        time.sleep(1)

        add_btn = safe_find_element(driver, By.CSS_SELECTOR, ".btn-handwrite")
        add_btn.click()
        time.sleep(0.5)

        # 找到关闭按钮（弹窗内的 .modal-close-btn）
        close_btn = safe_find_element(
            driver, By.CSS_SELECTOR, "#addModal .modal-close-btn"
        )
        assert close_btn is not None, "弹窗关闭按钮不存在"
        close_btn.click()
        time.sleep(0.5)

        # 验证弹窗关闭
        add_modal = safe_find_element(driver, By.ID, "addModal")
        modal_classes = add_modal.get_attribute("class")
        assert "active" not in modal_classes, "弹窗未关闭"

        take_screenshot(driver, "test_add_modal_close")
        print("[通过] 添加记录弹窗正常关闭")

    def test_add_record_form_submit(self, driver):
        """测试新增记录表单提交"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 打开弹窗
        add_btn = safe_find_element(driver, By.CSS_SELECTOR, ".btn-handwrite")
        add_btn.click()
        time.sleep(0.5)

        # 填写表单
        title_input = safe_find_element(driver, By.ID, "recordTitle")
        title_input.clear()
        title_input.send_keys("测试电影_自动化")

        # 选择评分（选4星）
        star4_label = safe_find_element(
            driver, By.CSS_SELECTOR, '#addModal label[for="star4"]'
        )
        if star4_label:
            star4_label.click()
            time.sleep(0.2)

        # 选择心情
        mood_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '#addModal .mood-btn[data-mood="😊"]'
        )
        if mood_btn:
            mood_btn.click()
            time.sleep(0.2)

        # 填写短评
        comment = safe_find_element(driver, By.ID, "recordComment")
        if comment:
            comment.clear()
            comment.send_keys("这是自动化测试添加的记录")

        # 填写标签
        tags_input = safe_find_element(driver, By.ID, "recordTags")
        if tags_input:
            tags_input.clear()
            tags_input.send_keys("测试 自动化")

        # 提交表单（点击"📌 贴上去"按钮）
        submit_btn = safe_find_element(
            driver, By.CSS_SELECTOR, "#addModal .btn-journal-submit"
        )
        assert submit_btn is not None, "提交按钮不存在"
        submit_btn.click()
        time.sleep(1)

        # 验证弹窗关闭
        add_modal = safe_find_element(driver, By.ID, "addModal")
        modal_classes = add_modal.get_attribute("class")
        assert "active" not in modal_classes, "提交后弹窗未关闭"

        take_screenshot(driver, "test_add_record_submit")
        print("[通过] 新增记录提交成功")

    def test_filter_pills(self, driver):
        """测试记录筛选按钮"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到记录页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Records"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 查找筛选按钮
        pills = safe_find_elements(driver, By.CSS_SELECTOR, ".filter-pills .pill")
        assert len(pills) > 0, "筛选按钮 .pill 不存在"

        # 检查"全部"按钮默认是active
        all_pill = safe_find_element(
            driver, By.CSS_SELECTOR, '.pill[data-filter="all"]'
        )
        assert all_pill is not None, "全部筛选按钮不存在"
        assert "active" in all_pill.get_attribute("class"), "全部按钮未默认激活"

        # 点击电影筛选
        movie_pill = safe_find_element(
            driver, By.CSS_SELECTOR, '.pill[data-filter="电影"]'
        )
        if movie_pill:
            movie_pill.click()
            time.sleep(0.5)
            assert "active" in movie_pill.get_attribute("class"), "电影筛选按钮未激活"

        take_screenshot(driver, "test_filter_pills")
        print(f"[通过] 筛选按钮正常工作，共{len(pills)}个筛选选项")


class TestCalendarPage:
    """月历页测试"""

    def test_calendar_page_loads(self, driver):
        """检查月历页加载"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到月历页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Calendar"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 检查月历网格
        calendar_grid = safe_find_element(driver, By.ID, "calendarGrid")
        assert calendar_grid is not None, "#calendarGrid 不存在"

        # 检查月份标签
        month_label = safe_find_element(driver, By.ID, "calMonthLabel")
        assert month_label is not None, "#calMonthLabel 不存在"
        assert month_label.text != "", "月份标签为空"

        # 检查日期单元格
        cal_days = safe_find_elements(
            driver, By.CSS_SELECTOR, "#calendarGrid .cal-day:not(.empty)"
        )
        assert len(cal_days) > 0, "月历无日期单元格"

        take_screenshot(driver, "test_calendar_page")
        print(f"[通过] 月历页加载成功，当前月份: {month_label.text}")

    def test_calendar_navigation(self, driver):
        """测试月历前后月切换"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到月历页
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Calendar"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 记录当前月份
        month_label = safe_find_element(driver, By.ID, "calMonthLabel")
        original_month = month_label.text

        # 点击前一月按钮（使用cal-nav-btn定位）
        nav_btns = safe_find_elements(driver, By.CSS_SELECTOR, ".cal-nav-btn")
        assert len(nav_btns) >= 2, "月历导航按钮不足"

        # 第一个是"◀"（上一月），第二个是"▶"（下一月）
        prev_btn = nav_btns[0]
        prev_btn.click()
        time.sleep(0.5)

        new_month = month_label.text
        assert new_month != original_month, "点击上一月后月份未变化"

        take_screenshot(driver, "test_calendar_navigation")
        print(f"[通过] 月历导航正常: {original_month} -> {new_month}")


class TestLoginPage:
    """登录页测试"""

    def test_login_page_structure(self, driver):
        """检查登录页结构"""
        driver.get(LOGIN_URL)
        time.sleep(1)

        # 先清除登录状态以查看登录页
        driver.execute_script("localStorage.removeItem('cinelog_user');")
        driver.get(LOGIN_URL)
        time.sleep(1)

        # 检查登录卡片
        login_card = safe_find_element(driver, By.CSS_SELECTOR, ".login-card")
        assert login_card is not None, "登录卡片 .login-card 不存在"

        # 检查标题
        login_title = safe_find_element(driver, By.CSS_SELECTOR, ".login-title")
        assert login_title is not None, ".login-title 不存在"
        assert "我的光影手账" in login_title.text, f"登录标题不正确: {login_title.text}"

        # 检查Tab切换按钮
        tab_login = safe_find_element(driver, By.ID, "tabLogin")
        tab_register = safe_find_element(driver, By.ID, "tabRegister")
        assert tab_login is not None, "#tabLogin 不存在"
        assert tab_register is not None, "#tabRegister 不存在"

        # 检查登录表单
        login_form = safe_find_element(driver, By.ID, "loginForm")
        assert login_form is not None, "#loginForm 不存在"

        # 检查输入框
        username_input = safe_find_element(driver, By.ID, "loginUsername")
        password_input = safe_find_element(driver, By.ID, "loginPassword")
        assert username_input is not None, "#loginUsername 不存在"
        assert password_input is not None, "#loginPassword 不存在"

        take_screenshot(driver, "test_login_page")
        print("[通过] 登录页结构完整")

        # 恢复登录状态
        driver.execute_script(
            """
            localStorage.setItem('cinelog_user', JSON.stringify({
                username: arguments[0],
                joinDate: new Date().toLocaleDateString('zh-CN')
            }));
            localStorage.setItem('cinelog_token', 'local_' + arguments[0]);
        """,
            TEST_USERNAME,
        )

    def test_login_register_tab_switch(self, driver):
        """测试登录/注册Tab切换"""
        driver.get(LOGIN_URL)
        time.sleep(1)

        driver.execute_script("localStorage.removeItem('cinelog_user');")
        driver.get(LOGIN_URL)
        time.sleep(1)

        # 点击注册Tab
        tab_register = safe_find_element(driver, By.ID, "tabRegister")
        assert tab_register is not None, "#tabRegister 不存在"
        tab_register.click()
        time.sleep(0.5)

        # 验证注册表单显示
        register_form = safe_find_element(driver, By.ID, "registerForm")
        assert register_form is not None, "#registerForm 不存在"
        assert register_form.is_displayed(), "注册表单未显示"

        # 验证登录表单隐藏
        login_form = safe_find_element(driver, By.ID, "loginForm")
        assert not login_form.is_displayed(), "登录表单未隐藏"

        # 检查注册表单的输入框
        reg_username = safe_find_element(driver, By.ID, "regUsername")
        reg_password = safe_find_element(driver, By.ID, "regPassword")
        reg_confirm = safe_find_element(driver, By.ID, "regConfirm")
        assert reg_username is not None, "#regUsername 不存在"
        assert reg_password is not None, "#regPassword 不存在"
        assert reg_confirm is not None, "#regConfirm 不存在"

        take_screenshot(driver, "test_login_register_switch")
        print("[通过] 登录/注册Tab切换正常")

        # 恢复登录状态
        driver.execute_script(
            """
            localStorage.setItem('cinelog_user', JSON.stringify({
                username: arguments[0],
                joinDate: new Date().toLocaleDateString('zh-CN')
            }));
            localStorage.setItem('cinelog_token', 'local_' + arguments[0]);
        """,
            TEST_USERNAME,
        )


class TestModals:
    """弹窗测试"""

    def test_edit_modal_structure(self, driver):
        """检查编辑弹窗结构"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 验证编辑弹窗DOM存在
        edit_modal = safe_find_element(driver, By.ID, "editModal")
        assert edit_modal is not None, "编辑弹窗 #editModal 不存在"

        # 检查编辑弹窗内的表单元素
        edit_title = safe_find_element(driver, By.ID, "editTitle")
        edit_type = safe_find_element(driver, By.ID, "editType")
        edit_date = safe_find_element(driver, By.ID, "editDate")
        edit_comment = safe_find_element(driver, By.ID, "editComment")

        assert edit_title is not None, "#editTitle 不存在"
        assert edit_type is not None, "#editType 不存在"
        assert edit_date is not None, "#editDate 不存在"
        assert edit_comment is not None, "#editComment 不存在"

        take_screenshot(driver, "test_edit_modal_structure")
        print("[通过] 编辑弹窗结构完整")

    def test_delete_modal_structure(self, driver):
        """检查删除确认弹窗结构"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 验证删除弹窗DOM存在
        delete_modal = safe_find_element(driver, By.ID, "deleteModal")
        assert delete_modal is not None, "删除弹窗 #deleteModal 不存在"

        # 检查删除提示文本
        delete_msg = safe_find_element(
            driver, By.CSS_SELECTOR, "#deleteModal .delete-message"
        )
        assert delete_msg is not None, "删除提示文本不存在"

        # 检查按钮
        cancel_btn = safe_find_element(
            driver, By.CSS_SELECTOR, "#deleteModal .btn-journal-cancel"
        )
        danger_btn = safe_find_element(
            driver, By.CSS_SELECTOR, "#deleteModal .btn-journal-danger"
        )
        assert cancel_btn is not None, "删除弹窗取消按钮不存在"
        assert danger_btn is not None, "删除弹窗确认按钮不存在"

        take_screenshot(driver, "test_delete_modal_structure")
        print("[通过] 删除确认弹窗结构完整")


class TestTheme:
    """主题切换测试"""

    def test_theme_toggle(self, driver):
        """测试主题切换按钮"""
        driver.get(INDEX_URL)
        time.sleep(2)

        # 切换到我的页面
        tab_btn = safe_find_element(
            driver, By.CSS_SELECTOR, '.tab-item[data-page="Profile"]'
        )
        tab_btn.click()
        time.sleep(1)

        # 获取当前主题
        current_theme = driver.execute_script(
            "return document.documentElement.getAttribute('data-theme')"
        )

        # 找到主题切换按钮（包含 themeIcon 的按钮）
        theme_btn = safe_find_element(
            driver, By.CSS_SELECTOR, ".passport-actions .btn-passport"
        )
        assert theme_btn is not None, "主题切换按钮不存在"
        theme_btn.click()
        time.sleep(0.5)

        # 验证主题已切换
        new_theme = driver.execute_script(
            "return document.documentElement.getAttribute('data-theme')"
        )
        assert new_theme != current_theme, (
            f"主题未切换: {current_theme} -> {new_theme}"
        )

        take_screenshot(driver, f"test_theme_toggle_{new_theme}")
        print(f"[通过] 主题切换成功: {current_theme} -> {new_theme}")

        # 切回原主题
        theme_btn.click()
        time.sleep(0.3)


# ========== 运行入口 ==========

if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-s",
            "--no-header",
        ]
    )
