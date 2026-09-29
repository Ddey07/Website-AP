---
# Leave the homepage title empty to use the site title
title: ""
date: 2026-09-29
type: landing

design:
  # Default section spacing
  spacing: "2rem"

sections:
  - block: hero
    id: hero
    content:
      announcement:
        text: "📄 New preprint: Bigraphical Matérn–Whittle processes for big multivariate spatial data."
        link:
          text: Read it
          url: https://arxiv.org/abs/2609.01950
      title: CADENCE Lab
      text: |
        <span class="lab-fullform"><b>C</b>ontextual <b>A</b>nalytics of <b>D</b>igital &amp; <b>E</b>nvironmental data for <b>N</b>eurobehavioral, <b>C</b>ircadian &amp; <b>E</b>motional health</span><br>
        **Statistics for the rhythms of health across space and time.**<br>
        We build theory and methods for multivariate stochastic processes to learn from wearables ⌚, smartphones 📱 and the environment 📍 — and use them to understand how mental health, sleep, physical activity and circadian rhythms unfold. Led by [Debangan Dey](/people/) in the [Department of Statistics, Texas A&M University](https://artsci.tamu.edu/statistics/).
      primary_action:
        text: Meet the team
        url: /people/
        icon: arrow-right
      secondary_action:
        text: Join us
        url: /join/
    design:
      no_padding: true
      css_class: lab-hero

  - block: markdown-wide
    id: markmap
    content:
      title: Research at a glance
      text: |
       <style>
        .markmap{
            position: relative;
            user-select: none; /* Disable text selection */
        }
        .markmap > svg {
        width: 100%;
        height: 400px;
        }
        .markmap text {
          font-size: 30px !important;
        }
        </style>

        <div class="markmap" data-options='{"zoom": false, "pan": false}'>
        <script type="text/template">
        - Our Research
          - Motivation
            - Digital Health Technologies
              - Objective Data
                - Physical Activity ⌚
                - Headband EEG 🎧
                - Continuous Glucose Monitor 🩸
                - Heart Rate ❤️
              - Subjective Data 
                - Ecological Momentary Assessment📱
            - Environmental Data
              - Temperature, Light, Greenspace etc. 📍
          - Theory and Methods
            - Multivariate Stochastic Processes (Space & Time)
            - Dynamic Structural Equation Modeling
            - Joint Framework for Mixed-type Data (Ordinal/Binary/Truncated)
            - Graphical Models
          - Applications
            - Mental & Physical Health Dynamics
            - Personalized Prediction 
            - Early Intervention of Mood Disorders
            - Global Mental Health
        </script>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@latest"></script>


  - block: features
    id: pillars
    content:
      title: What we work on
      items:
        - name: Theory & Methods
          icon: variable
          description: Multivariate stochastic processes in space and time, semiparametric Gaussian copulas for mixed-type data, multivariate functional PCA, dynamic structural equation models, and graphical models. [Learn more →](/research/)
        - name: Digital Health Technologies
          icon: device-phone-mobile
          description: Objective streams from wearables and sensors — activity, heart rate, EEG, glucose — combined with real-time self-reports of mood, energy, sleep and stress, to build digital phenotypes of mental health.
        - name: Environment & Context
          icon: map-pin
          description: Linking health dynamics to temperature, light, greenspace and the built environment through location tracking and spatial statistics, from mood disorders to youth physical activity.

  - block: people
    id: team
    content:
      title: The team
      user_groups:
        - Principal Investigator
        - PhD Students
        - Undergraduate Students
    design:
      compact: true
      columns: 5
      show_social: false

  - block: markdown-wide
    id: recent-updates
    content:
      title: Recent news
      text: |
        - **🚨 Looking for motivated students to work on statistical and machine learning methods for analyzing data from wearables ⌚️, smartphones 📱, with contextual location information📍!**
        - 📄 **September 2026**: New preprint — *[Bigraphical Matérn–Whittle (BMW) Processes for Fast Inference of Big Multivariate Spatial Data on General Domains](https://arxiv.org/abs/2609.01950)* with A. Manna and C. J. Geoga.
        - ⚽ **2026**: New preprint — *Do In-Match Hydration Breaks Alter Match Momentum? A Within-Match Case-Crossover Analysis of the 2026 FIFA World Cup*. [arXiv](https://arxiv.org/abs/2607.19783) · [GitHub](https://github.com/Ddey07/wc2026-hydration-momentum).
        - 🏆 **2026**: Our team has won the **[NIH Director's Challenge Innovation Award](https://oir.nih.gov/sourcebook/awards-fellowships-grant-opportunities/directors-challenge-innovation-award-program/2026-directors-challenge-awards#2026-directors-merikangas)** for *Biologic Rhythms and Environmental Contexts in Human Health: Integrating Epidemiology and Circadian Science* (PI: Kathleen Merikangas, NIMH; in collaboration with NIDDK, NHLBI, NIAAA, NIA, NHGRI, Northwestern, Nathan Kline Institute, Johns Hopkins, U Colorado, **Texas A&M**, and UT Southwestern). Debangan Dey (Texas A&M, Consultant) will oversee development of data management and analytic strategies for multilevel data, integrating intensive individual-level data with macro environmental factors.
        - ⚽ **2026**: Built a *[FIFA World Cup 2026 Bracket Predictor](https://debangandey.rbind.io/wc2026/)* with Claude — Monte Carlo bracket odds, live ticket & hotel prices, and a trip planner that ranks your 3 cheapest venues (with day-trip detection and Google Flights links) so you can finally settle the "go or not go" debate.
        - 💻 **2026**: Released *[M²FPCA](https://github.com/Ddey07/M2FPCA)* — an R package for Multivariate Functional Principal Component Analysis of mixed-type functional data (continuous, truncated, ordinal, and binary) via a latent Gaussian copula. Companion to *[SGCTools](https://github.com/Ddey07/SGCTools)*.
        - 📰 **2025**: Published *[Associations between daily outdoor temperature and subjective real-time ratings of emotional states and sleep in mood disorder subtypes](https://www.sciencedirect.com/science/article/pii/S0165032725023602)* in **Journal of Affective Disorders** — Featured by Texas A&M: *[Warmer Days, Better Moods? It's Complicated.](https://artsci.tamu.edu/news/2026/03/warmer-days-better-moods-its-complicated.html)*
        - 📄 **2026**: New preprint — *[Doubly-Unlinked Regression for Dependent Data](https://arxiv.org/abs/2603.19506)* with A. Burman and S. Choudhury.

        [All news →](/news/)

  - block: resume-biography-4
    id: about-pi
    content:
      # Choose a user profile to display (a folder name within `content/authors/`)
      username: admin
      text: ""
      # Show a call-to-action button under your biography? (optional)
      button:
        text: Download CV
        url: uploads/cv-llt.pdf
    design:
      css_class: light
      background:
        color: light
        image:
          # Add your image background to `assets/media/`.
          filename: white.svg
          filters:
            brightness: 1.0
          size: cover
          position: center
          parallax: false

  - block: cta-card
    id: join-cta
    content:
      title: Work with us
      text: We are looking for motivated PhD, master's and undergraduate students to work on statistical and machine learning methods for wearables ⌚️, smartphones 📱, and contextual location information 📍.
      button:
        text: How to join
        url: /join/
    design:
      card:
        css_class: "bg-primary-700"
---
