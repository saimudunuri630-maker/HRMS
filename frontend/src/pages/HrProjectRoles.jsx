import React, { useState, useEffect, useRef } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Plus,
  ArrowLeft,
  Search,
  Users,
  CheckCircle2,
  AlertCircle,
  X,
  Trash2,
  Edit2,
  Briefcase,
  Loader2,
  FolderKanban,
  Filter,
  Check,
  UserCheck,
  ChevronDown,
  UserPlus
} from "lucide-react";
import { projectService, projectRoleService, employeeService } from "../services/api";
import "../styles/Projects.css";

export default function HrProjectRoles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(
    searchParams.get("projectId") || ""
  );
  const [roles, setRoles] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingRoles, setLoadingRoles] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Notifications
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Create Role Modal
  const [createRoleModal, setCreateRoleModal] = useState(false);
  const [createRoleForm, setCreateRoleForm] = useState({
    project_id: "",
    role_name: "",
    required_count: 1,
    description: "",
  });
  const [submittingCreate, setSubmittingCreate] = useState(false);

  // Edit Role Modal
  const [editRoleModal, setEditRoleModal] = useState(null);
  const [editRoleForm, setEditRoleForm] = useState({
    role_name: "",
    required_count: 1,
    description: "",
  });
  const [submittingEdit, setSubmittingEdit] = useState(false);

  // Delete Role Confirm
  const [deleteConfirmRole, setDeleteConfirmRole] = useState(null);
  const [submittingDelete, setSubmittingDelete] = useState(false);

  // Role Assignment State inside Edit Modal
  const empDropdownRef = useRef(null);
  const [allEmployees, setAllEmployees] = useState([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [assignedEmployees, setAssignedEmployees] = useState([]);
  const [loadingAssigned, setLoadingAssigned] = useState(false);
  const [selectedEmpIds, setSelectedEmpIds] = useState([]);
  const [empSearch, setEmpSearch] = useState("");
  const [empDropdownOpen, setEmpDropdownOpen] = useState(false);
  const [submittingAssign, setSubmittingAssign] = useState(false);
  const [removingAssignId, setRemovingAssignId] = useState(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (empDropdownRef.current && !empDropdownRef.current.contains(e.target)) {
        setEmpDropdownOpen(false);
      }
    };
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, []);


  const showNotification = (type, text) => {
    setNotification({ type, text });
    setTimeout(() => {
      setNotification({ type: "", text: "" });
    }, 4500);
  };

  const fetchProjects = async () => {
    try {
      setLoadingProjects(true);
      const res = await projectService.listProjects({ page_size: 100 });
      const items = res.items || [];

      const urlProjId = searchParams.get("projectId");
      let targetId = selectedProjectId;

      if (urlProjId) {
        const found = items.find((p) => String(p.id) === String(urlProjId));
        if (found) {
          targetId = String(urlProjId);
        } else {
          // Attempt to load the specific project by ID in case it's not in first page
          try {
            const single = await projectService.getProject(urlProjId);
            if (single && single.id) {
              items.unshift(single);
              targetId = String(urlProjId);
            } else {
              showNotification("error", "Project not found.");
              targetId = items.length > 0 ? String(items[0].id) : "";
            }
          } catch {
            showNotification("error", "Project not found.");
            targetId = items.length > 0 ? String(items[0].id) : "";
          }
        }
      } else if (!targetId && items.length > 0) {
        targetId = String(items[0].id);
      } else if (targetId && !items.some((p) => String(p.id) === String(targetId))) {
        targetId = items.length > 0 ? String(items[0].id) : "";
      }

      setProjects(items);
      setSelectedProjectId(targetId);
    } catch (err) {
      console.error("Failed to load projects:", err);
      showNotification("error", "Unable to load enterprise projects.");
    } finally {
      setLoadingProjects(false);
    }
  };

  const fetchRoles = async (projId) => {
    try {
      setLoadingRoles(true);
      const data = await projectRoleService.listRoles({ project_id: projId });
      setRoles(data || []);
    } catch (err) {
      console.error("Failed to fetch project roles:", err);
      showNotification("error", "Failed to retrieve project roles.");
    } finally {
      setLoadingRoles(false);
    }
  };

  const fetchEmployees = async () => {
    try {
      setLoadingEmployees(true);
      const res = await employeeService.listEmployees({ limit: 100 });
      const empList = res.employees || res.items || (Array.isArray(res) ? res : []);
      const activeEmps = empList.filter(
        (e) => (e.employment_status === "ACTIVE" || !e.employment_status) && !e.deleted_at
      );
      setAllEmployees(activeEmps);
    } catch (err) {
      console.error("Failed to load employees for assignment:", err);
    } finally {
      setLoadingEmployees(false);
    }
  };

  // Load Projects & Dynamic Employees on Mount & on window focus (for dynamic update after create)
  useEffect(() => {
    fetchProjects();
    fetchEmployees();

    const handleFocus = () => {
      fetchProjects();
      fetchEmployees();
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, []);


  // When selected project changes, fetch its roles and sync URL
  useEffect(() => {
    if (selectedProjectId) {
      fetchRoles(selectedProjectId);
      setSearchParams({ projectId: selectedProjectId });
    } else {
      setRoles([]);
    }
  }, [selectedProjectId]);

  const handleOpenCreateRole = () => {
    if (!selectedProjectId) {
      showNotification("error", "Please select a project first.");
      return;
    }
    setCreateRoleForm({
      project_id: selectedProjectId,
      role_name: "",
      required_count: 1,
      description: "",
    });
    setCreateRoleModal(true);
  };

  const handleCreateRoleSubmit = async (e) => {
    e.preventDefault();
    const cleanName = createRoleForm.role_name.trim();
    if (!cleanName) {
      showNotification("error", "Role name is required.");
      return;
    }
    const targetProjId = parseInt(selectedProjectId, 10);
    if (!targetProjId) {
      showNotification("error", "Please select a valid project.");
      return;
    }

    try {
      setSubmittingCreate(true);
      await projectRoleService.createRole({
        project_id: targetProjId,
        role_name: cleanName,
        required_count: parseInt(createRoleForm.required_count, 10) || 1,
        description: createRoleForm.description?.trim() || null,
      });

      showNotification("success", `Project role '${cleanName}' created successfully.`);
      setCreateRoleModal(false);

      // Refresh roles for the selected project immediately
      await fetchRoles(targetProjId);
    } catch (err) {
      console.error("Failed to create role:", err);
      const msg = err.response?.data?.detail || "Could not create project role.";
      showNotification("error", typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setSubmittingCreate(false);
    }
  };

  const fetchRoleAssignments = async (roleId, projId = null) => {
    try {
      setLoadingAssigned(true);
      const targetProjId = projId || editRoleModal?.project_id || selectedProjectId;
      const data = await projectRoleService.getAssignedEmployees(roleId, targetProjId);
      const records = Array.isArray(data) ? data : (data?.assignments || data?.items || []);
      setAssignedEmployees(records);
      return records;
    } catch (err) {
      console.error("Failed to fetch assigned employees:", err);
      try {
        const fallback = await projectRoleService.getAssignedEmployees(roleId, null);
        const fallbackRecords = Array.isArray(fallback) ? fallback : (fallback?.assignments || fallback?.items || []);
        setAssignedEmployees(fallbackRecords);
        return fallbackRecords;
      } catch (e) {
        console.error("Direct fallback failed:", e);
      }
      return [];
    } finally {
      setLoadingAssigned(false);
    }
  };

  const handleOpenEditRole = async (role) => {
    // 1. Reset selection, search, and clear assignment state immediately to avoid showing stale data from previous role
    setSelectedEmpIds([]);
    setEmpSearch("");
    setEmpDropdownOpen(false);
    setAssignedEmployees([]);
    setLoadingAssigned(true);

    // 2. Set current role and form state
    setEditRoleModal(role);
    setEditRoleForm({
      role_name: role.role_name || role.name || "",
      required_count: role.required_count || 1,
      description: role.description || "",
    });

    // 3. Load active employees and fresh role assignments for this specific role
    fetchEmployees();
    await fetchRoleAssignments(role.id, role.project_id);
  };

  const handleAssignEmployees = async () => {
    if (!editRoleModal) return;
    if (selectedEmpIds.length === 0) {
      showNotification("error", "Please select at least one employee to assign.");
      return;
    }

    const currentCount = assignedEmployees.length;
    const reqCount = parseInt(editRoleForm.required_count, 10) || 1;
    if (currentCount >= reqCount) {
      showNotification("error", `Required headcount of ${reqCount} has already been reached for this role.`);
      return;
    }
    if (currentCount + selectedEmpIds.length > reqCount) {
      const remaining = reqCount - currentCount;
      showNotification(
        "error",
        `Cannot assign ${selectedEmpIds.length} employee(s). Only ${remaining} open position(s) remaining (Headcount: ${reqCount}).`
      );
      return;
    }

    try {
      setSubmittingAssign(true);
      const targetProjId = editRoleModal.project_id || selectedProjectId;

      // Synchronize role headcount to database if changed in the modal form before assigning
      if (
        reqCount !== (editRoleModal.required_count || 1) ||
        editRoleForm.role_name.trim() !== (editRoleModal.role_name || editRoleModal.name || "").trim()
      ) {
        await projectRoleService.updateRole(editRoleModal.id, {
          role_name: editRoleForm.role_name.trim(),
          required_count: reqCount,
          description: editRoleForm.description?.trim() || null,
        });
        setEditRoleModal((prev) => ({
          ...prev,
          role_name: editRoleForm.role_name.trim(),
          required_count: reqCount,
          description: editRoleForm.description?.trim() || null,
        }));
      }

      const res = await projectRoleService.assignEmployees(
        editRoleModal.id,
        selectedEmpIds,
        targetProjId,
        { required_count: reqCount }
      );

      showNotification("success", res.message || "Employees assigned successfully.");

      // Check backend returned assignment records directly
      const returnedAssignments = Array.isArray(res?.assignments) ? res.assignments : [];

      // 1. Immediately update state with returned actual records from the backend
      if (returnedAssignments.length > 0) {
        setAssignedEmployees((prev) => {
          const map = new Map();
          (prev || []).forEach((item) => map.set(Number(item.employee_id), item));
          returnedAssignments.forEach((item) => map.set(Number(item.employee_id), item));
          return Array.from(map.values());
        });
      }

      // 2. Fetch fresh records directly from the database query endpoint
      await fetchRoleAssignments(editRoleModal.id, targetProjId);

      // 3. Clear successfully assigned employees from the temporary selected list
      setSelectedEmpIds([]);
      setEmpSearch("");
      setEmpDropdownOpen(false);

      // 4. Refresh roles list to update headcount indicator in the main role list
      await fetchRoles(targetProjId);
    } catch (err) {
      console.error("Failed to assign employees:", err);
      const msg = err.response?.data?.detail || "Failed to assign employees to role.";
      showNotification("error", typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setSubmittingAssign(false);
    }
  };

  const handleRemoveEmployee = async (assignmentId, employeeName) => {
    if (!editRoleModal) return;
    try {
      setRemovingAssignId(assignmentId);
      const targetProjId = editRoleModal.project_id || selectedProjectId;
      await projectRoleService.removeEmployee(
        editRoleModal.id,
        assignmentId,
        targetProjId
      );
      showNotification("success", `Removed ${employeeName || "employee"} from role.`);

      // Optimistically remove from state immediately
      setAssignedEmployees((prev) => prev.filter((a) => (a.assignment_id || a.id) !== assignmentId));

      // Re-fetch from DB
      await fetchRoleAssignments(editRoleModal.id, targetProjId);
      await fetchRoles(targetProjId);
    } catch (err) {
      console.error("Failed to remove employee assignment:", err);
      const msg = err.response?.data?.detail || "Could not remove employee from role.";
      showNotification("error", typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setRemovingAssignId(null);
    }
  };

  const availableFilteredEmployees = allEmployees.filter((emp) => {
    if (!emp) return false;
    const searchLower = empSearch.toLowerCase().trim();
    if (!searchLower) return true;
    const fullName = `${emp.first_name || ""} ${emp.last_name || ""}`.toLowerCase();
    const code = (emp.employee_code || "").toLowerCase();
    const email = (emp.email || "").toLowerCase();
    const desig = (emp.official_designation || emp.designation || "").toLowerCase();
    return (
      fullName.includes(searchLower) ||
      code.includes(searchLower) ||
      email.includes(searchLower) ||
      desig.includes(searchLower)
    );
  });

  const handleEditRoleSubmit = async (e) => {
    e.preventDefault();
    if (!editRoleModal) return;
    const cleanName = editRoleForm.role_name.trim();
    if (!cleanName) {
      showNotification("error", "Role name cannot be empty.");
      return;
    }

    try {
      setSubmittingEdit(true);
      await projectRoleService.updateRole(editRoleModal.id, {
        role_name: cleanName,
        required_count: editRoleForm.required_count || 1,
        description: editRoleForm.description?.trim() || null,
      });

      showNotification("success", `Project role '${cleanName}' updated successfully.`);
      setEditRoleModal((prev) => ({
        ...prev,
        role_name: cleanName,
        required_count: editRoleForm.required_count || 1,
        description: editRoleForm.description?.trim() || null,
      }));
      await fetchRoles(selectedProjectId);
    } catch (err) {
      console.error("Failed to update role:", err);
      const msg = err.response?.data?.detail || "Could not update project role.";
      showNotification("error", msg);
    } finally {
      setSubmittingEdit(false);
    }
  };


  const handleDeleteRole = async () => {
    if (!deleteConfirmRole) return;
    try {
      setSubmittingDelete(true);
      await projectRoleService.deleteRole(deleteConfirmRole.id);
      showNotification("success", `Role '${deleteConfirmRole.role_name}' removed.`);
      setDeleteConfirmRole(null);
      await fetchRoles(selectedProjectId);
    } catch (err) {
      console.error("Failed to delete role:", err);
      const msg =
        err.response?.data?.detail ||
        "This role is currently assigned to employees. Reassign those employees before removing the role.";
      showNotification("error", msg);
    } finally {
      setSubmittingDelete(false);
    }
  };

  // Filtered roles
  const filteredRoles = roles.filter((r) => {
    const matchesSearch =
      !searchQuery ||
      r.role_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === "ALL" || (statusFilter === "ACTIVE" && r.status === "ACTIVE");

    return matchesSearch && matchesStatus;
  });

  const selectedProject = projects.find((p) => String(p.id) === String(selectedProjectId));

  const reqCount = Math.max(1, parseInt(editRoleForm.required_count, 10) || 1);
  const currentAssignedCount = assignedEmployees.length;
  const isCapacityReached = !loadingAssigned && currentAssignedCount >= reqCount;
  const remainingCapacity = Math.max(0, reqCount - currentAssignedCount);

  return (
    <div className="prj-page-wrapper">
      {/* TOP HEADER */}
      <header className="prj-header-bar">
        <div className="prj-header-container">
          <div className="prj-header-left">
            <Link to="/hr/projects" className="prj-back-btn">
              <ArrowLeft size={16} /> Back to Projects
            </Link>
            <div className="prj-header-meta">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldCheck size={22} color="#047857" />
                <h2>Project Roles Service</h2>
              </div>
              <span>Manage project-specific functional roles and employee position capacity</span>
            </div>
          </div>

          <div className="prj-header-actions">
            <button
              className="prj-primary-btn"
              onClick={handleOpenCreateRole}
              disabled={loadingProjects || projects.length === 0}
            >
              <Plus size={16} /> Create Project Role
            </button>
          </div>
        </div>
      </header>

      {/* NOTIFICATION BANNER */}
      {notification.text && (
        <div
          style={{
            maxWidth: "1400px",
            margin: "12px auto 0 auto",
            padding: "0 32px",
            width: "100%",
          }}
        >
          <div
            className={`prj-alert-banner ${
              notification.type === "success" ? "success" : "error"
            }`}
          >
            {notification.type === "success" ? (
              <CheckCircle2 size={18} />
            ) : (
              <AlertCircle size={18} />
            )}
            <span>{notification.text}</span>
            <button
              onClick={() => setNotification({ type: "", text: "" })}
              style={{
                marginLeft: "auto",
                background: "transparent",
                border: "none",
                cursor: "pointer",
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* MAIN CONTAINER */}
      <main className="prj-content-container prj-main-container project-page-container">
        {/* PROJECT SELECTOR & FILTER CONTROLS */}
        <section
          style={{
            background: "#ffffff",
            padding: "20px 24px",
            borderRadius: "14px",
            border: "1px solid #e2e8f0",
            marginBottom: "24px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "16px",
              alignItems: "flex-end",
              justifyContent: "space-between",
            }}
          >
            {/* Project Picker */}
            <div style={{ flex: "1 1 300px", minWidth: "260px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#334155",
                  marginBottom: "6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                }}
              >
                Select Project *
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => {
                  setSelectedProjectId(e.target.value);
                  setSearchQuery("");
                  setStatusFilter("ALL");
                }}
                className="prj-form-select"
                disabled={loadingProjects}
                style={{
                  height: "42px",
                  fontWeight: 600,
                  borderColor: "#cbd5e1",
                  background: "#ffffff",
                }}
              >
                {loadingProjects ? (
                  <option value="">Loading projects...</option>
                ) : projects.length === 0 ? (
                  <option value="">No projects available</option>
                ) : (
                  projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.project_name} ({p.project_code}) • {p.status}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Role Search */}
            <div style={{ flex: "1 1 240px", minWidth: "200px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#334155",
                  marginBottom: "6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                }}
              >
                Role Search
              </label>
              <div style={{ position: "relative" }}>
                <Search
                  size={15}
                  color="#94a3b8"
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                  }}
                />
                <input
                  type="text"
                  placeholder="Filter by role title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="prj-form-input"
                  style={{ paddingLeft: "36px", height: "42px" }}
                />
              </div>
            </div>

            {/* Status Filter */}
            <div style={{ width: "160px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#334155",
                  marginBottom: "6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                }}
              >
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="prj-form-select"
                style={{ height: "42px" }}
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
              </select>
            </div>
          </div>

          {/* ACTIVE PROJECT INFO BANNER */}
          {selectedProject && (
            <div
              style={{
                marginTop: "18px",
                padding: "14px 18px",
                background: "#f0fdf4",
                borderRadius: "10px",
                border: "1px solid #bbf7d0",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "#166534",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  Selected Project
                </span>
                <h4
                  style={{
                    margin: "2px 0 0 0",
                    fontSize: "16px",
                    fontWeight: 700,
                    color: "#064e3b",
                  }}
                >
                  {selectedProject.project_name}{" "}
                  <span
                    style={{
                      fontSize: "13px",
                      color: "#047857",
                      fontWeight: 600,
                    }}
                  >
                    ({selectedProject.project_code})
                  </span>
                </h4>
              </div>

              <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Project Roles:</span>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#064e3b" }}>
                    {roles.length} Defined
                  </div>
                </div>

                <Link
                  to={`/hr/projects`}
                  style={{
                    padding: "6px 12px",
                    background: "#ffffff",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#334155",
                    textDecoration: "none",
                  }}
                >
                  Open in Projects
                </Link>
              </div>
            </div>
          )}
        </section>

        {/* ROLES LIST */}
        <section>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
            }}
          >
            <div>
              <h3
                style={{
                  margin: 0,
                  fontSize: "18px",
                  fontWeight: 700,
                  color: "#0f172a",
                }}
              >
                Project Roles
              </h3>
              <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "#64748b" }}>
                Roles scoped exclusively to{" "}
                <strong>{selectedProject?.project_name || "the selected project"}</strong>
              </p>
            </div>
          </div>

          {loadingRoles ? (
            <div
              style={{
                textAlign: "center",
                padding: "60px 0",
                background: "#ffffff",
                borderRadius: "14px",
                border: "1px solid #e2e8f0",
              }}
            >
              <Loader2
                size={32}
                className="spinner text-emerald"
                style={{ margin: "0 auto 8px auto" }}
              />
              <p style={{ color: "#64748b" }}>Loading project roles...</p>
            </div>
          ) : filteredRoles.length > 0 ? (
            <div className="prj-cards-grid">
              {filteredRoles.map((r) => (
                <article
                  key={r.id}
                  className="prj-card"
                  style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}
                >
                  <div>
                    <div className="prj-card-header">
                      <div className="prj-card-title-group">
                        <span
                          className="prj-code-badge"
                          style={{ background: "#f0fdf4", color: "#166534" }}
                        >
                          <ShieldCheck size={12} style={{ marginRight: "4px" }} />
                          PROJECT ROLE
                        </span>
                        <h3 style={{ fontSize: "16px", marginTop: "4px" }}>{r.role_name}</h3>
                      </div>
                      <span className="prj-status-pill active">
                        <span className="dot" /> {r.status || "ACTIVE"}
                      </span>
                    </div>

                    <p
                      className="prj-card-desc"
                      style={{ minHeight: "44px", fontSize: "13px", color: "#475569" }}
                    >
                      {r.description || "Project functional responsibility within team deliverables."}
                    </p>

                    <div className="prj-card-meta-list" style={{ marginTop: "12px" }}>
                      <div className="prj-card-meta-item">
                        <span>Assigned Employees:</span>
                        <strong style={{ color: r.assigned_count > 0 ? "#047857" : "#64748b" }}>
                          {r.assigned_count || 0} Employees
                        </strong>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Required Headcount:</span>
                        <strong>{r.required_count || 1} Positions</strong>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Open Capacity:</span>
                        <strong>{r.open_count || 0} Remaining</strong>
                      </div>
                    </div>
                  </div>

                  <div className="prj-card-actions" style={{ marginTop: "16px", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className="prj-primary-btn"
                      style={{ padding: "6px 12px", fontSize: "12px" }}
                      onClick={() => handleOpenEditRole(r)}
                      title="Assign employees and edit role parameters"
                    >
                      <UserCheck size={13} />
                      <span>Assign / Edit</span>
                    </button>

                    <button
                      type="button"
                      className="prj-btn-ghost text-danger"
                      onClick={() => setDeleteConfirmRole(r)}
                      title="Delete role"
                    >
                      <Trash2 size={13} />
                      <span>Delete</span>
                    </button>
                  </div>
                </article>

              ))}
            </div>
          ) : (
            <div
              className="prj-empty-box"
              style={{
                background: "#ffffff",
                borderRadius: "14px",
                border: "1px solid #e2e8f0",
                padding: "48px 24px",
              }}
            >
              <ShieldCheck
                size={48}
                color="#047857"
                style={{ margin: "0 auto 12px auto" }}
              />
              <h4>No Roles Found</h4>
              <p>
                {searchQuery
                  ? `No roles matched "${searchQuery}" in this project.`
                  : "No project roles registered under this project yet."}
              </p>
              <button
                className="prj-primary-btn"
                onClick={handleOpenCreateRole}
                style={{ marginTop: "16px" }}
                disabled={!selectedProjectId}
              >
                <Plus size={16} /> Create Project Role
              </button>
            </div>
          )}
        </section>
      </main>

      {/* ========================================================
          MODAL 1: CREATE PROJECT ROLE
          ======================================================== */}
      {createRoleModal && (
        <div className="prj-modal-overlay" onClick={() => setCreateRoleModal(false)}>
          <div
            className="prj-modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "500px" }}
          >
            <div className="prj-modal-header">
              <div>
                <h3>Create Project Role</h3>
                <p>Define functional role for {selectedProject?.project_name || "the selected project"}</p>
              </div>
              <button
                className="prj-modal-close"
                onClick={() => setCreateRoleModal(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateRoleSubmit}>
              <div className="prj-modal-body">
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div className="prj-form-group">
                    <label>Project (Read-Only Context)</label>
                    <div
                      style={{
                        padding: "10px 14px",
                        background: "#f0fdf4",
                        border: "1px solid #bbf7d0",
                        borderRadius: "8px",
                      }}
                    >
                      <strong style={{ display: "block", color: "#064e3b", fontSize: "14px" }}>
                        {selectedProject?.project_name || "Selected Project"}
                      </strong>
                      <span
                        style={{
                          fontSize: "12px",
                          color: "#047857",
                          fontWeight: 600,
                        }}
                      >
                        {selectedProject?.project_code}
                      </span>
                    </div>
                  </div>

                  <div className="prj-form-group">
                    <label>Role Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. DevOps Engineer"
                      value={createRoleForm.role_name}
                      onChange={(e) =>
                        setCreateRoleForm({ ...createRoleForm, role_name: e.target.value })
                      }
                      required
                      className="prj-form-input"
                    />
                    <small style={{ color: "#64748b", fontSize: "11px", marginTop: "4px" }}>
                      Must be unique within this project.
                    </small>
                  </div>

                  <div className="prj-form-group">
                    <label>Required Positions / Headcount</label>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={createRoleForm.required_count}
                      onChange={(e) =>
                        setCreateRoleForm({
                          ...createRoleForm,
                          required_count: parseInt(e.target.value, 10) || 1,
                        })
                      }
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group">
                    <label>Description</label>
                    <textarea
                      rows={3}
                      placeholder="Responsible for deployment, infrastructure, and CI/CD pipelines..."
                      value={createRoleForm.description}
                      onChange={(e) =>
                        setCreateRoleForm({ ...createRoleForm, description: e.target.value })
                      }
                      className="prj-form-textarea"
                    />
                  </div>
                </div>
              </div>

              <div className="prj-modal-footer">
                <button
                  type="button"
                  className="prj-btn-ghost"
                  onClick={() => setCreateRoleModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="prj-primary-btn"
                  disabled={submittingCreate || !createRoleForm.role_name.trim()}
                >
                  {submittingCreate ? "Creating..." : "Create Role"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 2: EDIT PROJECT ROLE + ASSIGN EMPLOYEES SECTION
          ======================================================== */}
      {editRoleModal && (
        <div className="prj-modal-overlay" onClick={() => setEditRoleModal(null)}>
          <div
            className="prj-modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "680px", width: "95%" }}
          >
            <div className="prj-modal-header">
              <div>
                <h3>Edit Project Role</h3>
                <p>Modify role parameters & assign employees to {selectedProject?.project_name || "the project"}</p>
              </div>
              <button className="prj-modal-close" onClick={() => setEditRoleModal(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="prj-modal-body" style={{ maxHeight: "78vh", overflowY: "auto", padding: "24px 28px" }}>
              {/* SECTION 1: ROLE INFORMATION (EXISTING FIELDS PRESERVED) */}
              <div style={{ marginBottom: "8px" }}>
                <h4
                  style={{
                    fontSize: "13px",
                    fontWeight: 700,
                    color: "#064e3b",
                    margin: "0 0 14px 0",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <ShieldCheck size={15} /> Role Information
                </h4>

                <form onSubmit={handleEditRoleSubmit}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div className="prj-form-group">
                      <label>Role Name *</label>
                      <input
                        type="text"
                        value={editRoleForm.role_name}
                        onChange={(e) =>
                          setEditRoleForm({ ...editRoleForm, role_name: e.target.value })
                        }
                        required
                        className="prj-form-input"
                      />
                    </div>

                    <div className="prj-form-group">
                      <label>Required Headcount</label>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={editRoleForm.required_count}
                        onChange={(e) => {
                          const val = e.target.value;
                          setEditRoleForm({
                            ...editRoleForm,
                            required_count: val === "" ? "" : Math.max(1, parseInt(val, 10) || 1),
                          });
                        }}
                        className="prj-form-input"
                      />
                    </div>

                    <div className="prj-form-group">
                      <label>Description</label>
                      <textarea
                        rows={2}
                        value={editRoleForm.description}
                        onChange={(e) =>
                          setEditRoleForm({ ...editRoleForm, description: e.target.value })
                        }
                        className="prj-form-textarea"
                      />
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end" }}>
                      <button
                        type="submit"
                        className="prj-btn-ghost"
                        style={{ borderColor: "#047857", color: "#047857", fontWeight: 600 }}
                        disabled={submittingEdit || !editRoleForm.role_name.trim()}
                      >
                        {submittingEdit ? "Saving..." : "Save Changes"}
                      </button>
                    </div>
                  </div>
                </form>
              </div>

              {/* CLEAR VISUAL SEPARATION */}
              <hr style={{ border: "none", borderTop: "1px solid #e2e8f0", margin: "24px 0" }} />

              {/* SECTION 2: NEW ASSIGN EMPLOYEES SECTION */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "10px",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div>
                    <h4
                      style={{
                        fontSize: "14px",
                        fontWeight: 700,
                        color: "#0f172a",
                        margin: 0,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <Users size={16} color="#047857" /> Assign Employees
                    </h4>
                    <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "#64748b" }}>
                      Select employees to assign to this project role.
                    </p>
                  </div>

                  {/* Headcount Capacity Tracker */}
                  <div
                    style={{
                      padding: "4px 10px",
                      borderRadius: "9999px",
                      fontSize: "12px",
                      fontWeight: 600,
                      background: isCapacityReached ? "#fef3c7" : "#ecfdf5",
                      color: isCapacityReached ? "#92400e" : "#065f46",
                      border: `1px solid ${isCapacityReached ? "#fde68a" : "#a7f3d0"}`,
                    }}
                  >
                    Headcount: {currentAssignedCount} / {reqCount} Filled
                    {isCapacityReached && " (Capacity Reached)"}
                  </div>
                </div>

                {/* Headcount Alert if Capacity Reached */}
                {isCapacityReached && (
                  <div
                    style={{
                      padding: "10px 14px",
                      background: "#fffbeb",
                      border: "1px solid #fef3c7",
                      borderRadius: "8px",
                      fontSize: "12px",
                      color: "#92400e",
                      marginBottom: "14px",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <AlertCircle size={15} color="#b45309" style={{ flexShrink: 0 }} />
                    <span>
                      Required headcount of {reqCount} has been reached for this
                      role. Increase Required Headcount above to assign additional employees.
                    </span>
                  </div>
                )}

                {/* EMPLOYEE MULTI-SELECT SEARCH & DROPDOWN */}
                <div ref={empDropdownRef} style={{ position: "relative", marginBottom: "12px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      border: "1px solid #cbd5e1",
                      borderRadius: "8px",
                      background: isCapacityReached ? "#f8fafc" : "#ffffff",
                      padding: "7px 12px",
                      cursor: isCapacityReached ? "not-allowed" : "pointer",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                    }}
                    onClick={() => {
                      if (!isCapacityReached) {
                        setEmpDropdownOpen(!empDropdownOpen);
                      }
                    }}
                  >
                    <Search size={15} color="#64748b" style={{ marginRight: "8px", flexShrink: 0 }} />
                    <input
                      type="text"
                      placeholder={
                        isCapacityReached
                          ? "Capacity reached. Increase headcount above to assign more."
                          : selectedEmpIds.length === 1
                          ? `${(() => {
                              const emp = allEmployees.find((e) => e.id === selectedEmpIds[0]);
                              return emp
                                ? `${emp.first_name || ""} ${emp.last_name || ""} (${emp.employee_code || ""}) — 1 employee selected`
                                : "1 employee selected";
                            })()}`
                          : selectedEmpIds.length > 1
                          ? `${selectedEmpIds.length} employees selected`
                          : "Select Employees / Search Employees by Name, ID, or Designation..."
                      }
                      value={empSearch}
                      disabled={isCapacityReached}
                      onChange={(e) => {
                        setEmpSearch(e.target.value);
                        if (!empDropdownOpen) setEmpDropdownOpen(true);
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!isCapacityReached) setEmpDropdownOpen(true);
                      }}
                      style={{
                        border: "none",
                        outline: "none",
                        width: "100%",
                        fontSize: "13px",
                        color: "#0f172a",
                        background: "transparent",
                        fontFamily: "inherit",
                        cursor: isCapacityReached ? "not-allowed" : "text",
                      }}
                    />
                    <ChevronDown
                      size={16}
                      color="#64748b"
                      style={{
                        transform: empDropdownOpen ? "rotate(180deg)" : "none",
                        transition: "transform 0.2s",
                        flexShrink: 0,
                      }}
                    />
                  </div>

                  {/* DROPDOWN POPUP */}
                  {empDropdownOpen && (
                    <div
                      style={{
                        position: "absolute",
                        top: "100%",
                        left: 0,
                        right: 0,
                        marginTop: "4px",
                        background: "#ffffff",
                        border: "1px solid #cbd5e1",
                        borderRadius: "8px",
                        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
                        zIndex: 60,
                        maxHeight: "240px",
                        overflowY: "auto",
                      }}
                    >
                      {loadingEmployees ? (
                        <div
                          style={{
                            padding: "16px",
                            textAlign: "center",
                            color: "#64748b",
                            fontSize: "13px",
                          }}
                        >
                          <Loader2
                            size={16}
                            className="spinner"
                            style={{ display: "inline", marginRight: "6px" }}
                          />
                          Loading employee roster...
                        </div>
                      ) : availableFilteredEmployees.length > 0 ? (
                        <>
                          {availableFilteredEmployees.map((emp) => {
                            const isSelected = selectedEmpIds.includes(emp.id);
                            const isAlreadyAssigned = assignedEmployees.some(
                              (a) => a.employee_id === emp.id
                            );
                            const empFullName = `${emp.first_name || ""} ${emp.last_name || ""}`.trim();
                            const designation =
                              emp.official_designation || emp.designation || "Team Member";

                            return (
                              <div
                                key={emp.id}
                                onClick={() => {
                                  if (isAlreadyAssigned) return;
                                  if (isSelected) {
                                    setSelectedEmpIds(selectedEmpIds.filter((id) => id !== emp.id));
                                  } else {
                                    if (isCapacityReached) {
                                      showNotification(
                                        "error",
                                        `Capacity reached (${reqCount}/${reqCount}). Increase required headcount to assign more.`
                                      );
                                      return;
                                    }
                                    if (remainingCapacity === 1) {
                                      setSelectedEmpIds([emp.id]);
                                      setEmpDropdownOpen(false);
                                    } else {
                                      if (selectedEmpIds.length >= remainingCapacity) {
                                        showNotification(
                                          "error",
                                          `Cannot select more than remaining capacity of ${remainingCapacity}.`
                                        );
                                        return;
                                      }
                                      const next = [...selectedEmpIds, emp.id];
                                      setSelectedEmpIds(next);
                                      if (next.length === remainingCapacity) {
                                        setEmpDropdownOpen(false);
                                      }
                                    }
                                  }
                                }}
                                style={{
                                  padding: "9px 12px",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  gap: "10px",
                                  borderBottom: "1px solid #f1f5f9",
                                  cursor: isAlreadyAssigned ? "not-allowed" : "pointer",
                                  background: isAlreadyAssigned
                                    ? "#f8fafc"
                                    : isSelected
                                    ? "#ecfdf5"
                                    : "#ffffff",
                                  opacity: isAlreadyAssigned ? 0.6 : 1,
                                  transition: "background 0.15s ease",
                                }}
                                onMouseEnter={(e) => {
                                  if (!isAlreadyAssigned && !isSelected)
                                    e.currentTarget.style.background = "#f1f5f9";
                                }}
                                onMouseLeave={(e) => {
                                  if (!isAlreadyAssigned && !isSelected)
                                    e.currentTarget.style.background = "#ffffff";
                                }}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                  <input
                                    type="checkbox"
                                    checked={isSelected || isAlreadyAssigned}
                                    disabled={isAlreadyAssigned}
                                    readOnly
                                    style={{
                                      accentColor: "#047857",
                                      cursor: isAlreadyAssigned ? "not-allowed" : "pointer",
                                      pointerEvents: "none",
                                    }}
                                  />
                                  <div>
                                    <div
                                      style={{
                                       fontSize: "13px",
                                        fontWeight: 600,
                                        color: "#0f172a",
                                      }}
                                    >
                                      {empFullName}{" "}
                                      <span
                                        style={{
                                          fontSize: "11px",
                                          color: "#047857",
                                          fontWeight: 700,
                                          marginLeft: "4px",
                                        }}
                                      >
                                        — {emp.employee_code}
                                      </span>
                                    </div>
                                    <div style={{ fontSize: "11px", color: "#64748b" }}>
                                      {emp.email || "No email"}{" "}
                                      {designation ? `• ${designation}` : ""}
                                    </div>
                                  </div>
                                </div>

                                {isAlreadyAssigned && (
                                  <span
                                    style={{
                                      fontSize: "11px",
                                      color: "#065f46",
                                      background: "#d1fae5",
                                      padding: "2px 8px",
                                      borderRadius: "4px",
                                      fontWeight: 600,
                                    }}
                                  >
                                    Assigned
                                  </span>
                                )}
                              </div>
                            );
                          })}

                          {/* Dropdown Multi-Select Footer */}
                          <div
                            style={{
                              padding: "8px 12px",
                              background: "#f8fafc",
                              borderTop: "1px solid #e2e8f0",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              position: "sticky",
                              bottom: 0,
                            }}
                          >
                            <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: 500 }}>
                              {selectedEmpIds.length} of {remainingCapacity} selected
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setEmpDropdownOpen(false);
                              }}
                              style={{
                                padding: "4px 12px",
                                fontSize: "11.5px",
                                fontWeight: 600,
                                background: "#047857",
                                color: "#ffffff",
                                border: "none",
                                borderRadius: "6px",
                                cursor: "pointer",
                              }}
                            >
                              Done
                            </button>
                          </div>
                        </>
                      ) : (
                        <div
                          style={{
                            padding: "16px",
                            textAlign: "center",
                            color: "#64748b",
                            fontSize: "13px",
                          }}
                        >
                          No active employees match "{empSearch}".
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* SELECTED EMPLOYEES CHIPS */}
                {selectedEmpIds.length > 0 && (
                  <div
                    style={{
                      marginBottom: "12px",
                      padding: "8px 12px",
                      background: "#f8fafc",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "6px",
                      }}
                    >
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "#475569" }}>
                        Selected ({selectedEmpIds.length}):
                      </span>
                      <button
                        type="button"
                        onClick={() => setSelectedEmpIds([])}
                        style={{
                          background: "none",
                          border: "none",
                          fontSize: "11px",
                          color: "#dc2626",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        Clear all
                      </button>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {selectedEmpIds.map((id) => {
                        const emp = allEmployees.find((e) => e.id === id);
                        if (!emp) return null;
                        return (
                          <span
                            key={id}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "6px",
                              padding: "4px 10px",
                              borderRadius: "9999px",
                              background: "#ecfdf5",
                              color: "#065f46",
                              border: "1px solid #a7f3d0",
                              fontSize: "12px",
                              fontWeight: 600,
                            }}
                          >
                            {emp.first_name} {emp.last_name} — {emp.employee_code}
                            <X
                              size={13}
                              style={{ cursor: "pointer", color: "#047857" }}
                              onClick={() =>
                                setSelectedEmpIds(selectedEmpIds.filter((empId) => empId !== id))
                              }
                            />
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* ASSIGN EMPLOYEES BUTTON ON THE RIGHT SIDE */}
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "18px" }}>
                  <button
                    type="button"
                    className="prj-primary-btn"
                    onClick={handleAssignEmployees}
                    disabled={
                      submittingAssign ||
                      selectedEmpIds.length === 0 ||
                      selectedEmpIds.length > remainingCapacity ||
                      isCapacityReached
                    }
                    style={{
                      opacity:
                        submittingAssign ||
                        selectedEmpIds.length === 0 ||
                        selectedEmpIds.length > remainingCapacity ||
                        isCapacityReached
                          ? 0.55
                          : 1,
                      cursor:
                        submittingAssign ||
                        selectedEmpIds.length === 0 ||
                        selectedEmpIds.length > remainingCapacity ||
                        isCapacityReached
                          ? "not-allowed"
                          : "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {submittingAssign ? (
                      <>
                        <Loader2 size={15} className="spinner" /> Assigning...
                      </>
                    ) : (
                      <>
                        <UserCheck size={15} /> Assign{" "}
                        {selectedEmpIds.length === 1
                          ? "Employee"
                          : selectedEmpIds.length > 1
                          ? `${selectedEmpIds.length} Employees`
                          : "Employees"}
                      </>
                    )}
                  </button>
                </div>

                {/* CURRENTLY ASSIGNED EMPLOYEES DISPLAY */}
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "8px",
                    }}
                  >
                    <h5
                      style={{
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "#334155",
                        margin: 0,
                      }}
                    >
                      Assigned Employees ({assignedEmployees.length})
                    </h5>
                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                      Required Headcount: {editRoleForm.required_count || 1}
                    </span>
                  </div>

                  {loadingAssigned ? (
                    <div style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>
                      <Loader2
                        size={20}
                        className="spinner text-emerald"
                        style={{ margin: "0 auto 6px auto" }}
                      />
                      <p style={{ fontSize: "12px", margin: 0 }}>Loading assigned employees...</p>
                    </div>
                  ) : assignedEmployees.length > 0 ? (
                    <div
                      style={{
                        border: "1px solid #e2e8f0",
                        borderRadius: "8px",
                        overflow: "hidden",
                        background: "#ffffff",
                      }}
                    >
                      {assignedEmployees.map((a, idx) => (
                        <div
                          key={a.assignment_id || a.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "12px 16px",
                            borderBottom:
                              idx < assignedEmployees.length - 1 ? "1px solid #f1f5f9" : "none",
                            gap: "12px",
                            flexWrap: "wrap",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                            <div
                              style={{
                                width: "32px",
                                height: "32px",
                                borderRadius: "50%",
                                background: "#ecfdf5",
                                color: "#047857",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontWeight: 700,
                                fontSize: "13px",
                                border: "1px solid #a7f3d0",
                                flexShrink: 0,
                              }}
                            >
                              {a.first_name
                                ? a.first_name[0]
                                : a.employee_name
                                ? a.employee_name[0]
                                : "E"}
                            </div>
                            <div>
                              <div
                                style={{
                                  fontSize: "13.5px",
                                  fontWeight: 600,
                                  color: "#0f172a",
                                }}
                              >
                                {a.full_name || a.employee_name}{" "}
                                <span
                                  style={{
                                    fontSize: "11px",
                                    color: "#047857",
                                    fontWeight: 700,
                                    marginLeft: "4px",
                                  }}
                                >
                                  — {a.employee_code}
                                </span>
                              </div>
                              <div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
                                {a.email && <span>{a.email} • </span>}
                                {a.designation && <span>{a.designation} • </span>}
                                <span>Assigned: {a.assigned_date}</span>
                              </div>
                            </div>
                          </div>

                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span
                              style={{
                                padding: "3px 10px",
                                borderRadius: "9999px",
                                fontSize: "11px",
                                fontWeight: 600,
                                background: "#ecfdf5",
                                color: "#047857",
                                border: "1px solid #a7f3d0",
                              }}
                            >
                              Assigned
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                handleRemoveEmployee(
                                  a.assignment_id || a.id,
                                  a.full_name || a.employee_name
                                )
                              }
                              disabled={removingAssignId === (a.assignment_id || a.id)}
                              style={{
                                background: "#fff",
                                border: "1px solid #fecaca",
                                borderRadius: "6px",
                                padding: "4px 10px",
                                fontSize: "11.5px",
                                fontWeight: 600,
                                color: "#dc2626",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                              }}
                              title="Remove employee from this role"
                            >
                              {removingAssignId === (a.assignment_id || a.id) ? (
                                <Loader2 size={12} className="spinner" />
                              ) : (
                                <Trash2 size={12} />
                              )}
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div
                      style={{
                        padding: "36px 24px",
                        textAlign: "center",
                        background: "#f8fafc",
                        borderRadius: "10px",
                        border: "1px dashed #cbd5e1",
                      }}
                    >
                      <UserCheck
                        size={32}
                        color="#047857"
                        style={{ margin: "0 auto 10px auto", opacity: 0.8, display: "block" }}
                      />
                      <div
                        style={{
                          fontSize: "13.5px",
                          fontWeight: 700,
                          color: "#1e293b",
                          marginBottom: "4px",
                        }}
                      >
                        No employees currently assigned to this role
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                        Select one or more employees from the dropdown above and click "Assign Employees".
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="prj-modal-footer">
              <button
                type="button"
                className="prj-btn-ghost"
                onClick={() => setEditRoleModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}


      {/* ========================================================
          MODAL 3: DELETE ROLE CONFIRMATION (WITH SAFETY CHECK)
          ======================================================== */}
      {deleteConfirmRole && (
        <div
          className="prj-modal-overlay"
          onClick={() => setDeleteConfirmRole(null)}
          style={{ zIndex: 120 }}
        >
          <div
            className="prj-modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "460px" }}
          >
            <div className="prj-modal-header" style={{ borderBottomColor: "#fee2e2" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "#fee2e2",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#dc2626",
                  }}
                >
                  <AlertCircle size={20} />
                </div>
                <div>
                  <h3 style={{ color: "#991b1b" }}>Delete Project Role</h3>
                  <p>Confirmation required</p>
                </div>
              </div>
              <button
                className="prj-modal-close"
                onClick={() => setDeleteConfirmRole(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="prj-modal-body">
              <p
                style={{
                  margin: "0 0 12px 0",
                  fontSize: "14px",
                  color: "#334155",
                  lineHeight: 1.5,
                }}
              >
                Are you sure you want to delete the role{" "}
                <strong>{deleteConfirmRole.role_name}</strong>?
              </p>

              {deleteConfirmRole.assigned_count > 0 ? (
                <div
                  style={{
                    padding: "12px 14px",
                    background: "#fef2f2",
                    borderRadius: "8px",
                    border: "1px solid #fecaca",
                    fontSize: "13px",
                    color: "#991b1b",
                    fontWeight: 600,
                  }}
                >
                  ⚠ This role is currently assigned to {deleteConfirmRole.assigned_count}{" "}
                  employee(s). Reassign those employees before removing the role.
                </div>
              ) : (
                <div
                  style={{
                    padding: "10px 14px",
                    background: "#f8fafc",
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                    color: "#64748b",
                  }}
                >
                  No employees are currently assigned to this role. Deletion will safely remove this
                  role from the project role registry.
                </div>
              )}
            </div>

            <div className="prj-modal-footer">
              <button
                type="button"
                className="prj-btn-ghost"
                onClick={() => setDeleteConfirmRole(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="prj-btn-action"
                style={{
                  background: "#dc2626",
                  color: "#ffffff",
                  opacity: deleteConfirmRole.assigned_count > 0 ? 0.6 : 1,
                  cursor: deleteConfirmRole.assigned_count > 0 ? "not-allowed" : "pointer",
                }}
                onClick={handleDeleteRole}
                disabled={submittingDelete || deleteConfirmRole.assigned_count > 0}
              >
                {submittingDelete ? "Deleting..." : "Delete Role"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
