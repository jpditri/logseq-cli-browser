require_relative 'test_helper'

class LogseqBrowserTest < Minitest::Test
  def setup
    # Initialize with a non-existent pages directory (no files needed)
    @browser = LogseqBrowser.new('nonexistent_pages')
  end

  def test_change_theme_valid
    original = SELECTED_THEME.dup
    @browser.send(:change_theme, 'matrix')
    assert_equal 'matrix', SELECTED_THEME
    assert_equal THEMES['matrix'], COLORS
    # Restore original theme
    @browser.send(:change_theme, original)
    assert_equal original, SELECTED_THEME
  end

  def test_change_theme_invalid_does_not_modify
    original = SELECTED_THEME.dup
    @browser.send(:change_theme, 'invalid_theme')
    assert_equal original, SELECTED_THEME
    assert_equal THEMES[original], COLORS
  end

  def test_show_theme_menu_no_console
    # Ensure no error when console not available
    def @browser.console_available?; false; end
    assert_nil @browser.send(:show_theme_menu)
  end

  def test_show_chat_popup_no_console
    # Ensure no error when console not available
    def @browser.console_available?; false; end
    assert_nil @browser.send(:show_chat_popup, left_width: 0, width: 80)
  end
end