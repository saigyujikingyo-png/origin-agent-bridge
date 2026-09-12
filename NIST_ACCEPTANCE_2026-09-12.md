# NIST observed-data acceptance: 2026-09-12

The first device used installed Origin Companion **0.2.7** through MCP with licensed standard Origin 2026b SR2 (10.350243), x64, non-Demo. Four public NIST **Observed Data** sets supplied 299 observations. Independent calculations used the Python standard library; actual Origin produced fits, figures and projects. This record does not replace SR1, 0.2.8 or other-host acceptance.

| Dataset and original study | Rows | Native processing and checks |
| --- | ---: | --- |
| [Norris](https://www.itl.nist.gov/div898/strd/lls/data/Norris.shtml): ozone instrument calibration | 36 | Free-intercept, unweighted fit; slope 1.0021168180204543, intercept -0.26232307377398456, RSS 26.617398529423433; matched certified values and independent OLS |
| [Misra1a](https://www.itl.nist.gov/div898/strd/nls/data/misra1a.shtml): adsorption experiment | 14 | ExpAssoc1 with TD=0, Yb=0; A=238.942129216123, Tau=1817.66483561682, RSS 0.12455138894440412 |
| [Eckerle4](https://www.itl.nist.gov/div898/strd/nls/data/eckerle4.shtml): interference-filter transmittance | 35 | Gauss with y0=0; xc=451.541218169202, w=8.17766491630347, A=3.89625980462372, RSS 0.0014635887487304512; derived FWHM=9.628464633228877 |
| [Chwirut1](https://www.itl.nist.gov/div898/strd/nls/data/chwirut1.shtml): ultrasonic calibration | 214 | Uniquely named user FDF for exp(-b1*x)/(b2+b3*x); RSS 2384.477149865835; native n=214, mean=30.26149532710281, sample SD=23.67979265052397 |

Predeclared nonlinear parameter tolerances were relative 1e-4 and absolute 1e-8; RSS relative tolerance was 1e-5. Passing does not mean recovering every published significant digit. Misra maps Tau=1/b2; Eckerle maps A=b1√(2π), w=2b2. FWHM is derived from model width, not acceptance of an independent peak-analysis module.

Original files order columns y,x; import changed them to x,y while preserving every row. StRD files supplied no measurement units, so figures say units unspecified. No assumed units, SD error bars or weights were added. Chwirut scatter grouped at common x is descriptive, not measurement uncertainty.

All four projects were saved/reopened and x/y checked value by value. A saved nonlinear project was opened in a persistent session, retitled and closed, then reopened in a new Origin instance; data and the edit persisted. Identical requests reused the same job; stale revisions were rejected without revision change. The native continued-edit step took 0.938 seconds, not the total cloud-model time.

The four selected final figures produced 12 PNG/PDF/SVG files with matching manifest hashes. PNGs were decoded and viewed; each one-page PDF was independently rendered/viewed; SVG parsed successfully. Initial nonlinear title/legend layout issues were corrected and exports rechecked. The figures below are the final reviewed selections, not proof that every automatic report graph was visually reviewed.

![Native Norris linear fit](origin-agent/verification/nist-figures/Norris.png)
![Native Misra1a nonlinear fit](origin-agent/verification/nist-figures/Misra1a.png)
![Native Eckerle4 Gaussian fit](origin-agent/verification/nist-figures/Eckerle4.png)
![Native Chwirut1 custom-function fit](origin-agent/verification/nist-figures/Chwirut1.png)

Two failures are retained: a test incorrectly treated WSheet.lt_exec's None return as boolean success, then native statistics passed after correcting the assertion; a correctly rejected session input path appeared as a generic host serialization error in 0.2.7, prompting 0.2.8's structured-error fix. Failed jobs reached terminal states; polling was not presented as recovery.

Sources, hashes, certified parameters, tolerances, results and artifact checks are in the [sanitised machine-readable record](origin-agent/verification/nist-observed-2026-09-12.json). Only results from public NIST data are published, without coursework, accounts, secrets or private university download links.
