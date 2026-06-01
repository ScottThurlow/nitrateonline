# Nitrate Online

An independent film criticism publication founded by Carrie Gorringe in 1996. The site published in-depth reviews, feature essays, and international film festival coverage until 2004, operated by Nitrate Productions, Inc.

The name refers to the nitrate film stock used in cinema's early decades — a material of great beauty, sensitivity, and historical significance.

**Live site:** [nitrateonline.com](https://nitrateonline.com)

## Archive Contents

- **1,900+ pages** of film reviews, features, and festival coverage
- Coverage spanning **1996–2004**
- Festival reporting from Berlin, Seattle (SIFF), Toronto (TIFF), and more
- Contributors including Carrie Gorringe, Eddie Cockrell, Gregory Avery, Sean Axmaker, and others

## Project Structure

```text
/                   Site root (index, about, search, archive pages)
/1996–2004/         Article pages organized by year
/images/            Review photos and site assets
/tools/             Build and conversion scripts
```

## Technology

- Static HTML site with a shared CSS design system (`nitrate.css`)
- Art-deco visual theme with gold/dark palette
- Responsive layout, semantic HTML, and accessibility features
- Deployed via cPanel with branch-based environments (main = production, ppe = staging)

## Environments

| Branch   | URL                     | Purpose                        |
| -------- | ----------------------- | ------------------------------ |
| `main`   | nitrateonline.com       | Production                     |
| `ppe`    | ppe.nitrateonline.com   | Staging/preview (not indexed)  |
| `bugfix` | —                       | Active development             |

## Contributing

External contributions require approval from a project maintainer. See the repository ruleset for details.

## License

All content (reviews, features, images) is copyright &copy; 1996–2004 Nitrate Productions, Inc. and its respective authors.

This work is licensed under a [Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You are free to share and adapt the content for any purpose, provided you give appropriate credit. Attribution should include the author name, "Nitrate Online," and a link to the original page on [nitrateonline.com](https://nitrateonline.com).

[![CC BY 4.0](https://licensebuttons.net/l/by/4.0/88x31.png)](https://creativecommons.org/licenses/by/4.0/)
