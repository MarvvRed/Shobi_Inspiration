# Perfume Inspiration Finder

A feature-rich, single-page web application designed to help users explore and find inspiration for "dupe" perfumes available on the Shobi website ([leparfum.com.gr/en/](https://leparfum.com.gr/en/)).

This application is built with vanilla JavaScript, Tailwind CSS, and several powerful libraries to provide a fast, beautiful, and user-friendly experience. It loads all its data from the external `parfumer_beriget_ai.json` file.

## Credits

This repository is based on the original **Shobi Inspiration** project by [smellyCat-deep](https://github.com/smellyCat-deep).

Original repository: [smellyCat-deep/shobi_inspiration](https://github.com/smellyCat-deep/shobi_inspiration)

This repository is an independent copy maintained and modified by **MarvvRed**.

## Features

* **Dynamic Data Loading:** All perfume data is loaded asynchronously from a local JSON file, making it easy to update the collection.

* **Advanced Search & Filtering:**

  * A powerful real-time search that queries across all perfume attributes (brand, name, notes, etc.).

  * Filter by Brand, Perfume Type (Men, Women, Unisex, Niche), and multiple Scent Notes simultaneously using an intuitive combo box.

* **Dual View Modes:**

  * **Card View:** A responsive, visually appealing grid layout perfect for browsing.

  * **Table View:** A sortable and paginated table view powered by Grid.js, ideal for quickly analyzing and comparing data.

* **User-Centric Tools:**

  * **Favorites System:** Mark perfumes with a heart icon to save them to a personal list, which is stored locally in the browser.

  * **Shopping Cart:** Collect perfume codes in a slide-out cart.

  * **Copy Codes:** Easily copy all collected codes to the clipboard with a single click, ready to be used on the Shobi website.

* **Interactive Dashboard:**

  * Visualize the data with charts (powered by Chart.js) showing breakdowns of perfumes per brand and by scent type.

  * See interesting, dynamically calculated stats about the perfume collection.

* **Customizable Themes:**

  * Switch between four beautiful, pre-built color themes (Solarized Dark, Dracula, Nord, and Gruvbox Light) to suit your preference. Your choice is saved for your next visit.

* **Performance Optimized:**

  * The card view uses a "lazy loading" approach, initially displaying a subset of results and allowing the user to load more, ensuring a fast initial startup even with thousands of products.

## How to Use

1. Clone or download the repository.

2. Place your `parfumer_beriget_ai.json` file in the same root directory as the `index.html` file.

3. Open `index.html` in any modern web browser.

## Disclaimer

This project is an independent creation and is intended solely for personal, inspirational, and non-commercial use.

* **No Affiliation:** I am not affiliated, associated, authorized, endorsed by, or in any way officially connected with Shobi ([leparfum.com.gr](https://leparfum.com.gr)) or any of the original perfume brands mentioned in the data. All product and company names are trademarks™ or registered® trademarks of their respective holders.

* **Data Accuracy:** The perfume data provided in the JSON file is compiled for inspirational purposes. I do not take responsibility for its accuracy, completeness, or timeliness. The data should not be considered an official source.

## License

This project is licensed under the **GPL-3.0 License**. See the `LICENSE` file for details.
