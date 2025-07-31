# Telegram Data Product Pipeline

A robust solution for extracting, storing, and transforming public Telegram channel data focused on health topics in Ethiopia. This pipeline leverages Python, PostgreSQL, and dbt to enable scalable ELT workflows.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Design](#system-design)
- [Directory Layout](#directory-layout)
- [Setup Guide](#setup-guide)
- [Pipeline Execution](#pipeline-execution)
- [Data Organization](#data-organization)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [How to Contribute](#how-to-contribute)
- [License & Support](#license--support)

---

## Overview

This project implements an ELT pipeline to generate insights from Telegram health discussions:

- **Extraction:** Python scripts collect messages and media from Telegram channels.
- **Loading:** Raw data is organized in a Data Lake and ingested into PostgreSQL.
- **Transformation:** dbt models reshape the data for analytics.

---

## Key Features

- Automated Telegram scraping using Telethon.
- Partitioned Data Lake for raw messages and images.
- Reliable Python loader for repeatable PostgreSQL ingestion.
- dbt models for staging, dimensions, and facts, with built-in tests.
- Incremental updates for efficient processing.
- Data validation via dbt tests and custom checks.

---

