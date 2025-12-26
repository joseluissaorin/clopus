---
name: wordpress-theme
description: Develop custom WordPress themes with modern best practices
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
  - Glob
triggers:
  - wordpress
  - wp theme
  - wordpress theme
  - php theme
---

# WordPress Theme Development

## Context

You are an expert WordPress developer creating custom themes using:
- PHP 8.0+
- WordPress 6.0+
- Block Editor (Gutenberg) support
- Modern CSS/SCSS
- Webpack/Vite for assets

## Theme Structure

```
my-theme/
├── style.css              # Theme metadata
├── functions.php          # Theme setup
├── index.php              # Fallback template
├── front-page.php         # Homepage
├── single.php             # Single post
├── page.php               # Single page
├── archive.php            # Archive pages
├── header.php             # Header partial
├── footer.php             # Footer partial
├── sidebar.php            # Sidebar partial
├── 404.php                # 404 page
├── search.php             # Search results
├── comments.php           # Comments template
├── template-parts/        # Reusable parts
│   ├── content.php
│   ├── content-single.php
│   └── content-none.php
├── inc/                   # PHP includes
│   ├── template-functions.php
│   ├── template-tags.php
│   └── customizer.php
├── assets/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/             # Page templates
│   └── template-full-width.php
├── patterns/              # Block patterns
├── parts/                 # Block template parts
├── theme.json             # Block theme config
└── screenshot.png         # Theme screenshot
```

## Instructions

### 1. Theme Header (style.css)

```css
/*
Theme Name: My Theme
Theme URI: https://example.com/theme
Author: Your Name
Author URI: https://example.com
Description: A custom WordPress theme
Version: 1.0.0
Requires at least: 6.0
Tested up to: 6.4
Requires PHP: 8.0
License: GNU General Public License v2 or later
License URI: http://www.gnu.org/licenses/gpl-2.0.html
Text Domain: my-theme
Tags: custom-logo, custom-menu, featured-images, full-site-editing
*/
```

### 2. Theme Setup (functions.php)

```php
<?php
/**
 * Theme functions and definitions
 */

if (!defined('ABSPATH')) {
    exit;
}

define('MY_THEME_VERSION', '1.0.0');

function my_theme_setup() {
    // Add theme support
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('html5', [
        'search-form',
        'comment-form',
        'comment-list',
        'gallery',
        'caption',
        'style',
        'script',
    ]);
    add_theme_support('custom-logo', [
        'height' => 100,
        'width' => 400,
        'flex-height' => true,
        'flex-width' => true,
    ]);
    add_theme_support('editor-styles');
    add_theme_support('wp-block-styles');
    add_theme_support('responsive-embeds');

    // Register menus
    register_nav_menus([
        'primary' => __('Primary Menu', 'my-theme'),
        'footer' => __('Footer Menu', 'my-theme'),
    ]);
}
add_action('after_setup_theme', 'my_theme_setup');

function my_theme_scripts() {
    wp_enqueue_style(
        'my-theme-style',
        get_stylesheet_uri(),
        [],
        MY_THEME_VERSION
    );

    wp_enqueue_style(
        'my-theme-main',
        get_template_directory_uri() . '/assets/css/main.css',
        [],
        MY_THEME_VERSION
    );

    wp_enqueue_script(
        'my-theme-main',
        get_template_directory_uri() . '/assets/js/main.js',
        [],
        MY_THEME_VERSION,
        true
    );
}
add_action('wp_enqueue_scripts', 'my_theme_scripts');

function my_theme_widgets_init() {
    register_sidebar([
        'name' => __('Sidebar', 'my-theme'),
        'id' => 'sidebar-1',
        'description' => __('Add widgets here.', 'my-theme'),
        'before_widget' => '<section id="%1$s" class="widget %2$s">',
        'after_widget' => '</section>',
        'before_title' => '<h2 class="widget-title">',
        'after_title' => '</h2>',
    ]);
}
add_action('widgets_init', 'my_theme_widgets_init');
```

### 3. theme.json (Block Editor Config)

```json
{
  "$schema": "https://schemas.wp.org/trunk/theme.json",
  "version": 2,
  "settings": {
    "color": {
      "palette": [
        { "slug": "primary", "color": "#0066cc", "name": "Primary" },
        { "slug": "secondary", "color": "#333333", "name": "Secondary" }
      ]
    },
    "typography": {
      "fontFamilies": [
        {
          "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          "slug": "system",
          "name": "System"
        }
      ],
      "fontSizes": [
        { "slug": "small", "size": "0.875rem", "name": "Small" },
        { "slug": "medium", "size": "1rem", "name": "Medium" },
        { "slug": "large", "size": "1.25rem", "name": "Large" }
      ]
    },
    "spacing": {
      "units": ["px", "em", "rem", "%", "vw", "vh"]
    },
    "layout": {
      "contentSize": "800px",
      "wideSize": "1200px"
    }
  },
  "styles": {
    "color": {
      "background": "var(--wp--preset--color--white)",
      "text": "var(--wp--preset--color--secondary)"
    }
  }
}
```

### 4. Header Template

```php
<?php
/**
 * Header template
 */
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<header id="masthead" class="site-header">
    <div class="container">
        <div class="site-branding">
            <?php if (has_custom_logo()): ?>
                <?php the_custom_logo(); ?>
            <?php else: ?>
                <a href="<?php echo esc_url(home_url('/')); ?>">
                    <?php bloginfo('name'); ?>
                </a>
            <?php endif; ?>
        </div>

        <nav id="site-navigation" class="main-navigation">
            <?php
            wp_nav_menu([
                'theme_location' => 'primary',
                'menu_class' => 'primary-menu',
                'container' => false,
            ]);
            ?>
        </nav>
    </div>
</header>

<main id="primary" class="site-main">
```

## Best Practices

1. **Escape all output** - Use esc_html(), esc_attr(), esc_url()
2. **Use WordPress APIs** - Never write raw SQL
3. **Prefix functions** - Avoid naming conflicts
4. **Support translations** - Use __() and _e()
5. **Follow WPCS** - WordPress Coding Standards
6. **Use theme.json** - Modern block configuration
7. **Optimize performance** - Lazy load images, minimize assets

## Validation

- Run WordPress Theme Check plugin
- Test with Theme Unit Test data
- Validate accessibility (WCAG 2.1)
- Check responsive design
- Test with popular plugins
