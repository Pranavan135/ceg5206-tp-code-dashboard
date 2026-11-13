# CEG5206 Group Project Code Dashboard

A GitHub Pages dashboard for the 11 groups in CEG5206, Algorithms & Performance Optimization for Computing. The homepage lists the project repositories. The RepoSense report provides commit timelines, contributor breakdowns and line-level code authorship for the public repositories included in each build.

Seven repository URLs are configured. Groups 01, 04, 07 and 09 are waiting for links.

## Publish on GitHub Pages

1. Unzip the download. Create an **empty public repository** on GitHub, for example `ceg5206-code-dashboard`. Leave the README, licence and `.gitignore` options unchecked on GitHub. The download already includes the files for the site and its workflow.
2. Open Terminal in the extracted `ceg5206-code-dashboard` folder. Replace `YOUR-USERNAME` with your GitHub username or organization. If you chose a different repository name, change it in the remote URL as well.

   ```bash
   git init -b main
   git add .
   git commit -m "Add CEG5206 code dashboard"
   git remote add origin https://github.com/pranavan135/ceg5206-tp-code-dashboard.git
   git push -u origin main
   ```

3. In the GitHub repository, go to **Settings → Pages**. Under **Build and deployment → Source**, select **GitHub Actions**. The supplied workflow handles publication.
4. Go to **Actions → Publish CEG5206 dashboard → Run workflow**. Select **main**, then click **Run workflow**. This also works if the first push triggered a run before Pages was enabled.
5. Open the URL shown by the successful **Deploy to GitHub Pages** job, or find it under **Settings → Pages**. With the example name, the URL is `https://YOUR-USERNAME.github.io/ceg5206-code-dashboard/`.

The workflow rebuilds on pushes to `main`, on manual runs, and daily at approximately 8:17 a.m. Singapore time. Commits pushed to the project repositories will appear after a successful refresh. GitHub can delay scheduled runs and disables them after 60 days of inactivity in public repositories. If needed, re-enable the workflow in **Actions** and run it manually.

[GitHub Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [Scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## Add a repository

Edit `groups.json` and replace the corresponding `null` with the project's full GitHub URL in quotes. Use the Group 01 entry below as a template.

```json
{ "id": "01", "url": "https://github.com/OWNER/REPOSITORY" }
```

Commit and push the change, or edit the file on GitHub and commit to `main`. The next build regenerates both the directory and the RepoSense report. Leave `null` for any group still waiting for a link.

## Preview locally

For the directory, install Python 3.10 or newer and run these commands from the extracted project folder.

```bash
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

Open [http://localhost:8000](http://localhost:8000). The directory preview works offline. Stop the server with **Ctrl+C**.

For the full report, install Git and Java 21, and run the build with internet access.

```bash
python3 scripts/build.py --jar vendor/RepoSense.jar
python3 -m http.server 8000 --directory dist
```

The report follows each repository's default branch and uses its available history. To limit a build to a project period, pass `--since DD/MM/YYYY` and `--until DD/MM/YYYY`. Add the same options to the build command in `.github/workflows/pages.yml` to apply those dates to published reports.

## Understand the report

- The build fetches project repositories anonymously. If a supplied link is private, missing or otherwise unavailable, the dashboard still shows the group and its link. A report built from other accessible repositories can still be published.
- GitHub Pages serves the report publicly. RepoSense can publish source code, commit messages and contributor identities from the analyzed repositories. Check that the public report is suitable for your course before sharing the Pages URL.
- Commit and authorship figures describe activity visible in the analyzed Git history. Work on branches that have not reached the analyzed branch, and work outside Git, may be absent.
- If the site has an older report, check the latest **Publish CEG5206 dashboard** run. The build log explains repository access and report generation failures. A failed run leaves the previous successful deployment in place.

[RepoSense documentation](https://reposense.org/RepoSense/ug/) · [GitHub Pages visibility](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#about-publishing-sources)

## Source layout

| Path | Purpose |
| --- | --- |
| `groups.json` | Course title, group numbers and project links |
| `site/` | Dashboard HTML, CSS and JavaScript |
| `scripts/build.py` | Builds the site and generates the RepoSense data |
| `vendor/` | RepoSense JAR from the reference dashboard and its licence |
| `.github/workflows/pages.yml` | Builds and publishes the dashboard on GitHub Pages |
| `dist/` | Generated website for local preview and deployment |

The bundled RepoSense JAR is the one provided in the reference dashboard. Its manifest identifies build `524076bfc5`. RepoSense is MIT-licensed. [RepoSense upstream source](https://github.com/reposense/RepoSense) · [Upstream licence](https://github.com/reposense/RepoSense/blob/master/LICENSE)
