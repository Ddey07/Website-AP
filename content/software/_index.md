---
title: Software
cms_exclude: true

# View
view: card

# Optional cover image (relative to `assets/media/` folder).
image:
  caption: ''
  filename: ''
---

I develop and maintain open-source **R packages** implementing the statistical methods from my research on mixed-type functional and multivariate data. Both are available on GitHub.

## M²FPCA

**Multivariate Functional Principal Component Analysis for Mixed-Type Functional Data.** Joint covariance estimation and functional PCA for multiple functional variables measured on different scales — continuous, truncated, ordinal, and binary — over a common time domain. Built on a latent Gaussian copula, it produces shared temporal eigenfunctions and subject-level scores that borrow strength across variables, and supports regular grids as well as irregular, sparse, and asynchronous sampling.

[View on GitHub »](https://github.com/Ddey07/M2FPCA)

```r
remotes::install_github("Ddey07/M2FPCA")
```

## SGCTools

**Semiparametric Gaussian Copula tools for mixed and functional data.** Estimates latent correlations across continuous, truncated, ordinal (any number of categories), and binary data types, with covariance estimation and functional principal component analysis for mixed-type functional data. Implements the methods of Dey & Zipunnikov (2022) and Dey, Ghosal, Merikangas & Zipunnikov (2023).

[View on GitHub »](https://github.com/Ddey07/SGCTools)

```r
devtools::install_github("Ddey07/SGCTools")
```
