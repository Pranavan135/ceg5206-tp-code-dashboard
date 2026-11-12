"use strict";

const byId = (id) => document.getElementById(id);
const search = byId("group-search");
const statusFilter = byId("repository-status");
const table = byId("repository-table");
const rows = byId("repository-rows");
const rowTemplate = byId("repository-row-template");
const directoryMessage = byId("directory-message");
const reportDetail = byId("report-detail");
const reportUnavailable = byId("report-unavailable");

const singaporeTime = new Intl.DateTimeFormat("en-SG", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Singapore",
});
const groupList = new Intl.ListFormat("en-SG", { type: "conjunction" });

function githubPath(url) {
  if (typeof url !== "string") return null;

  const match = url.match(/^https:\/\/github\.com\/([\w.-]+\/[\w.-]+)\/?$/i);
  return match?.[1] ?? null;
}

function describeGroups(ids) {
  return `${ids.length === 1 ? "Group" : "Groups"} ${groupList.format(ids)}`;
}

function renderReport(report) {
  const timestamp = report.generatedAt ? new Date(report.generatedAt) : null;
  const generatedAt = timestamp && Number.isFinite(timestamp.valueOf())
    ? ` Updated ${singaporeTime.format(timestamp)} SGT.`
    : "";

  if (report.available) {
    byId("report-link").hidden = false;
    reportDetail.textContent = `Includes ${describeGroups(report.groups)}.${generatedAt}`;
  } else {
    reportDetail.textContent = report.generatedAt
      ? `The latest run did not produce a report.${generatedAt}`
      : "The contribution report has yet to be generated.";
  }

  if (report.unavailableGroups.length > 0) {
    reportUnavailable.textContent = `Analysis unavailable for ${describeGroups(report.unavailableGroups)}.`;
    reportUnavailable.hidden = false;
  }
}

function createRow(group) {
  const row = rowTemplate.content.firstElementChild.cloneNode(true);
  const label = `Group ${group.id}`;
  const repositoryPath = githubPath(group.url);
  const status = row.querySelector(".status");
  const repositoryLink = row.querySelector(".repository-link");

  row.querySelector(".group-name").textContent = label;
  status.textContent = repositoryPath ? "Linked" : "URL pending";
  status.classList.toggle("is-linked", Boolean(repositoryPath));

  if (repositoryPath) {
    repositoryLink.href = group.url;
    repositoryLink.querySelector(".repository-path").textContent = repositoryPath;
    repositoryLink.hidden = false;
  } else {
    row.querySelector(".repository-placeholder").hidden = false;
  }

  return { row, groupId: group.id, label, repositoryPath };
}

function renderDirectory(groups) {
  const entries = groups.map(createRow);
  const linkedCount = entries.filter((entry) => entry.repositoryPath).length;

  byId("group-count").textContent = entries.length;
  byId("linked-count").textContent = linkedCount;
  byId("pending-count").textContent = entries.length - linkedCount;
  byId("stats").hidden = false;
  byId("controls").hidden = false;

  rows.replaceChildren(...entries.map((entry) => entry.row));

  function applyFilters() {
    const query = search.value.trim().toLowerCase();
    const groupQuery = query.match(/^(?:group[\s-]*)?(\d{1,2})$/)?.[1];
    let visibleCount = 0;

    for (const entry of entries) {
      const status = entry.repositoryPath ? "linked" : "pending";
      const matchesQuery = !query
        || groupQuery?.padStart(2, "0") === entry.groupId
        || entry.label.toLowerCase().includes(query)
        || entry.repositoryPath?.toLowerCase().includes(query);
      const matchesStatus = statusFilter.value === "all" || statusFilter.value === status;
      entry.row.hidden = !(matchesQuery && matchesStatus);
      if (!entry.row.hidden) visibleCount += 1;
    }

    byId("result-count").textContent = `${visibleCount} of ${entries.length} groups`;
    table.hidden = visibleCount === 0;
    directoryMessage.hidden = visibleCount > 0;
    directoryMessage.textContent = "No groups match your search and filters.";
  }

  search.addEventListener("input", applyFilters);
  statusFilter.addEventListener("change", applyFilters);
  applyFilters();
}

async function loadDashboard() {
  try {
    const response = await fetch("./dashboard-data.json");
    if (!response.ok) throw new Error(`Dashboard data returned HTTP ${response.status}`);
    const { course, groups, report } = await response.json();

    const dashboardTitle = `${course.code} Code Dashboard`;
    document.title = dashboardTitle;
    byId("dashboard-title").textContent = dashboardTitle;
    byId("brand-code").textContent = course.code;
    byId("course-title").textContent = course.title;
    byId("footer-title").textContent = `${course.code} · ${course.title}`;

    renderReport(report);
    renderDirectory(groups);
  } catch (error) {
    console.error("Could not load dashboard data", error);
    reportDetail.textContent = "Report status is unavailable.";
    directoryMessage.textContent = "Could not load group repositories. Serve the generated site over HTTP and check that dashboard-data.json is present.";
  }
}

loadDashboard();
