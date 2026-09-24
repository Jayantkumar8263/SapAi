import { useEffect, useState } from "react";

import {
  Activity,
  BarChart3,
  CheckCircle2,
  CircleAlert,
  FileSpreadsheet,
  Home,
  Loader2,
  Play,
  RefreshCw,
  Settings,
  ShieldCheck,
  TrendingUp,
  Upload,
  XCircle,
  Download,
  Search,
  Filter,
  ArrowUpDown,
} from "lucide-react";

import "./App.css";


// =========================================================
// API CONFIGURATION
// =========================================================

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";


// =========================================================
// WORKFLOW STEPS
// =========================================================

const WORKFLOW_STEPS = [
  "Process Previous Inventory",
  "Process Current Inventory",
  "Compare Previous and Current Inventory",
  "Analyze Inventory Changes",
  "Classify RI / Capital Materials",
  "Generate Inventory Report",
  "Validate Generated Report",
];


// =========================================================
// MAIN APP
// =========================================================

function App() {

  // =======================================================
  // PAGE STATE
  // =======================================================

  const [activePage, setActivePage] = useState("dashboard");


  // =======================================================
  // BACKEND STATE
  // =======================================================

  const [backendStatus, setBackendStatus] =
    useState("checking");


  // =======================================================
  // AUTOMATION STATE
  // =======================================================

  const [running, setRunning] = useState(false);

  const [runningStep, setRunningStep] =
    useState(-1);

  const [workflowResult, setWorkflowResult] =
    useState(null);


  // =======================================================
  // UI STATE
  // =======================================================

  const [error, setError] = useState("");
  const [notification, setNotification] = useState("");

  const [resultSearch, setResultSearch] = useState("");
  const [resultFilter, setResultFilter] = useState("All");
  const [resultSort, setResultSort] = useState("none");

  // =======================================================
  // AUTOMATION CONFIGURATION
  // =======================================================

  const [previousPeriod, setPreviousPeriod] =
    useState("Previous Month");

  const [currentPeriod, setCurrentPeriod] =
    useState("Current Month");

  const [selectedPlant, setSelectedPlant] =
    useState("BSP");

  const [storageLocation, setStorageLocation] =
    useState("All");

  // =======================================================
  // INVENTORY FILE UPLOADS
  // =======================================================

  const [previousFile, setPreviousFile] =
    useState(null);

  const [currentFile, setCurrentFile] =
    useState(null);

  const [uploadingFiles, setUploadingFiles] =
    useState(false);


  // =========================================================
  // BACKEND HEALTH
  // =========================================================

  const checkBackend = async () => {

    try {

      setBackendStatus("checking");

      const response = await fetch(
        `${API_BASE_URL}/health`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );


      if (!response.ok) {
        throw new Error(
          `Backend returned HTTP ${response.status}`
        );
      }


      setBackendStatus("online");

    } catch (err) {

      console.error(
        "Backend health check failed:",
        err
      );

      setBackendStatus("offline");
    }
  };


  // =========================================================
  // INITIAL BACKEND CHECK
  // =========================================================

  useEffect(() => {

    checkBackend();

    const interval = setInterval(
      checkBackend,
      10000
    );

    return () => {
      clearInterval(interval);
    };

  }, []);


  // =========================================================
  // API RESPONSE HELPER
  // =========================================================

  const parseResponse = async (response) => {

    const contentType =
      response.headers.get("content-type") || "";


    if (contentType.includes("application/json")) {

      try {

        return await response.json();

      } catch {

        return {};
      }
    }


    const text = await response.text();

    return {
      detail: text,
    };
  };


  // =========================================================
  // UPLOAD INVENTORY FILES
  // =========================================================

  const uploadInventoryFiles = async () => {

    if (!previousFile) {
      throw new Error(
        "Please select the previous inventory Excel file."
      );
    }

    if (!currentFile) {
      throw new Error(
        "Please select the current inventory Excel file."
      );
    }

    const formData = new FormData();

    formData.append("previous_file", previousFile);
    formData.append("current_file", currentFile);

    setUploadingFiles(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/inventory/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await parseResponse(response);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
          data?.message ||
          "Inventory file upload failed."
        );
      }

      return data;
    } finally {
      setUploadingFiles(false);
    }
  };


  // =========================================================
  // RUN INVENTORY AUTOMATION
  // =========================================================

  const runAutomation = async () => {

    if (running) {
      return;
    }


    // -------------------------------------------------------
    // RESET UI
    // -------------------------------------------------------

    setRunning(true);

    setRunningStep(0);

    setError("");

    setNotification("");

    setWorkflowResult(null);

    let stepTimer;

    try {

      // -----------------------------------------------------
      // MAKE SURE BACKEND IS AVAILABLE
      // -----------------------------------------------------

      if (backendStatus !== "online") {

        await checkBackend();

      }


      // -----------------------------------------------------
      // UPLOAD SELECTED INVENTORY FILES
      // -----------------------------------------------------

      await uploadInventoryFiles();

      setNotification(
        "Inventory files uploaded successfully. Starting agent..."
      );


      // -----------------------------------------------------
      // REQUEST BODY
      // -----------------------------------------------------

      const requestBody = {

        user_id: "BSP_DASHBOARD_USER",

        tcode: "MC.1",

        variant: "B002159",

        plant: selectedPlant,

        previous_period: previousPeriod,

        current_period: currentPeriod,

        storage_location: storageLocation,

      };


      console.log(
        "Starting BSP inventory automation..."
      );

      console.log(
        "API:",
        `${API_BASE_URL}/agent/run`
      );

      console.log(
        "Request:",
        requestBody
      );


      // -----------------------------------------------------
      // VISUAL STEP PROGRESS
      // -----------------------------------------------------

      stepTimer = setInterval(() => {

        setRunningStep((current) => {

          if (current >= WORKFLOW_STEPS.length - 1) {

            return current;

          }

          return current + 1;

        });

      }, 1200);


      // -----------------------------------------------------
      // CALL FASTAPI AGENT
      // -----------------------------------------------------

      const response = await fetch(
        `${API_BASE_URL}/agent/run`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },

          body: JSON.stringify(
            requestBody
          ),
        }
      );


      clearInterval(stepTimer);


      // -----------------------------------------------------
      // READ RESPONSE
      // -----------------------------------------------------

      const data =
        await parseResponse(response);


      console.log(
        "Agent response:",
        data
      );


      // -----------------------------------------------------
      // HANDLE HTTP ERRORS
      // -----------------------------------------------------

      if (!response.ok) {

        const detail =
          data?.detail ||
          data?.message ||
          `Agent request failed with HTTP ${response.status}`;

        throw new Error(detail);
      }


      // -----------------------------------------------------
      // SAVE RESULT
      // -----------------------------------------------------

      setRunningStep(
        WORKFLOW_STEPS.length
      );

      setWorkflowResult(data);


      // -----------------------------------------------------
      // SUCCESS MESSAGE
      // -----------------------------------------------------

      setNotification(
        "Inventory automation completed successfully."
      );


      // -----------------------------------------------------
      // MOVE TO RESULTS
      // -----------------------------------------------------

      setActivePage("results");


    } catch (err) {

      console.error(
        "Inventory automation failed:",
        err
      );


      setError(
        err?.message ||
        "Unable to run inventory automation."
      );


    } finally {

      if (stepTimer) {
        clearInterval(stepTimer);
      }

      setRunning(false);

      setRunningStep(-1);
    }
  };


  // =========================================================
  // DOWNLOAD REPORT
  // =========================================================

  const downloadReport = async () => {

    try {

      setError("");

      setNotification(
        "Preparing inventory report..."
      );


      const response = await fetch(
        `${API_BASE_URL}/agent/report/download`,
        {
          method: "GET",
        }
      );


      if (!response.ok) {

        const data =
          await parseResponse(response);


        throw new Error(
          data?.detail ||
          `Report download failed with HTTP ${response.status}`
        );
      }


      const blob =
        await response.blob();


      const url =
        window.URL.createObjectURL(blob);


      const link =
        document.createElement("a");


      link.href = url;

      link.download =
        "BSP_Inventory_Report.xlsx";


      document.body.appendChild(link);

      link.click();

      link.remove();


      window.URL.revokeObjectURL(url);


      setNotification(
        "BSP Inventory Report downloaded successfully."
      );


    } catch (err) {

      console.error(
        "Report download failed:",
        err
      );


      setError(
        err?.message ||
        "Unable to download report."
      );
    }
  };


  // =========================================================
  // GET WORKFLOW STEPS
  // =========================================================

  const workflowSteps =
    workflowResult?.steps || [];


  // =========================================================
  // GET STEP STATUS
  // =========================================================

  const getStepStatus = (stepName) => {

    // -------------------------------------------------------
    // During execution use visual progress
    // -------------------------------------------------------

    if (running) {

      const index =
        WORKFLOW_STEPS.indexOf(stepName);


      if (index < runningStep) {
        return "completed";
      }


      if (index === runningStep) {
        return "running";
      }


      return "pending";
    }


    // -------------------------------------------------------
    // After execution use backend result
    // -------------------------------------------------------

    const step =
      workflowSteps.find(
        (item) =>
          item.step === stepName
      );


    return (
      step?.status ||
      "pending"
    );
  };


  // =========================================================
  // GET COMPARISON RESULT
  // =========================================================

  const comparisonResult =
    workflowResult?.comparison_result ||
    workflowResult?.results?.comparison ||
    null;


  // =========================================================
  // GET COMPARISON SUMMARY
  // =========================================================

  const comparisonSummary =
    comparisonResult?.summary ||
    workflowResult?.results?.comparison?.summary ||
    {};


  // =========================================================
  // SUMMARY VALUES
  // =========================================================

  const newMaterials =
    Number(
      comparisonSummary.new_materials ??
      0
    );


  const removedMaterials =
    Number(
      comparisonSummary.removed_materials ??
      0
    );


  const existingMaterials =
    Number(
      comparisonSummary.existing_materials ??
      0
    );


  const quantityChange =
    Number(
      comparisonSummary.total_quantity_change ??
      0
    );

  // =========================================================
  // GET AI INVENTORY ANALYSIS
  // =========================================================

  const inventoryAnalysis =
    workflowResult?.metadata?.inventory_analysis ||
    workflowResult?.results?.analysis ||
    null;

  const analysisData =
    inventoryAnalysis?.analysis ||
    inventoryAnalysis?.data ||
    inventoryAnalysis ||
    {};

  const analysisRisk =
    analysisData?.risk_level ??
    analysisData?.risk?.level ??
    "Not evaluated";

  const significantChanges =
    analysisData?.significant_changes ??
    [];

  const topIncreases =
    analysisData?.top_increases ??
    [];

  const topDecreases =
    analysisData?.top_decreases ??
    [];

  const recommendations =
    analysisData?.recommendations ??
    [];

  const zeroStockRaw =
    analysisData?.zero_stock_materials_count ??
    (
      Array.isArray(
        analysisData?.zero_stock_materials
      )
        ? analysisData.zero_stock_materials.length
        : analysisData?.zero_stock_materials
    ) ??
    analysisData?.zero_stock ??
    0;

  const zeroStockNumber = Number(zeroStockRaw);

  const zeroStockMaterials =
    Number.isFinite(zeroStockNumber)
      ? zeroStockNumber
      : 0;

  const significantChangeCount =
    Array.isArray(significantChanges)
      ? significantChanges.length
      : Number(
        analysisData?.significant_changes_count ??
        0
      );

  // =========================================================
  // COMPARISON ROWS
  // =========================================================

  const comparisonRows =
    Array.isArray(comparisonResult?.comparison)
      ? comparisonResult.comparison
      : Array.isArray(workflowResult?.results?.comparison?.comparison)
        ? workflowResult.results.comparison.comparison
        : [];


  // ---------------------------------------------------------
  // Normalize backend row fields
  // ---------------------------------------------------------

  const normalizedRows = comparisonRows.map(
    (row, index) => ({
      id: index,

      materialCode:
        row.Material_Code ??
        row.material_code ??
        row["Material Code"] ??
        row.material ??
        "-",

      materialName:
        row.Material_Name ??
        row.material_name ??
        row["Material Name"] ??
        row.name ??
        "-",

      previousQuantity:
        Number(
          row.Previous_Quantity ??
          row.previous_quantity ??
          row["Previous Quantity"] ??
          row.previous_qty ??
          0
        ),

      currentQuantity:
        Number(
          row.Current_Quantity ??
          row.current_quantity ??
          row["Current Quantity"] ??
          row.current_qty ??
          0
        ),

      quantityChange:
        Number(
          row.Quantity_Change ??
          row.quantity_change ??
          row["Quantity Change"] ??
          row.change ??
          0
        ),

      unit:
        row.Unit ??
        row.unit ??
        "-",

      plant:
        row.Plant ??
        row.plant ??
        "-",

      status:
        row.Status ??
        row.status ??
        "Existing",

      inventoryKey:
        row.Inventory_Key ??
        row.inventory_key ??
        row["Inventory Key"] ??
        "-",
    })
  );


  // =========================================================
  // RI / CAPITAL CLASSIFICATION
  // =========================================================

  const classificationResult =
    workflowResult?.metadata?.inventory_classification ||
    workflowResult?.results?.classification ||
    null;

  const classificationData =
    classificationResult?.classification ||
    classificationResult?.data ||
    {};

  const classificationReferencesAvailable =
    classificationResult?.references_available ??
    classificationData?.references_available ??
    true;

  const classificationWarnings =
    Array.isArray(classificationData?.warnings)
      ? classificationData.warnings
      : [];

  const classificationRowsRaw =
    Array.isArray(classificationResult?.comparison)
      ? classificationResult.comparison
      : Array.isArray(classificationResult?.results)
        ? classificationResult.results
        : [];

  const classificationRows =
    classificationRowsRaw.map((row, index) => ({
      id: `classification-${index}`,

      materialCode:
        row.Material_Code ??
        row.material_code ??
        row["Material Code"] ??
        row.material ??
        "-",

      materialName:
        row.Material_Name ??
        row.material_name ??
        row["Material Name"] ??
        row.name ??
        "-",

      inventoryType:
        row.Inventory_Type ??
        row.inventory_type ??
        row["Inventory Type"] ??
        row.classification ??
        "UNCLASSIFIED",

      classificationReason:
        row.Classification_Reason ??
        row.classification_reason ??
        row["Classification Reason"] ??
        row.reason ??
        "-",
    }));

  const classificationCounts = {
    ri: Number(
      classificationData?.ri_count ??
      classificationData?.RI_count ??
      classificationData?.ri_materials ??
      0
    ),
    capital: Number(
      classificationData?.capital_count ??
      classificationData?.CAPITAL_count ??
      classificationData?.capital_materials ??
      0
    ),
    normal: Number(
      classificationData?.normal_count ??
      classificationData?.NORMAL_count ??
      classificationData?.normal_materials ??
      0
    ),
    unclassified: Number(
      classificationData?.unclassified_count ??
      classificationData?.UNCLASSIFIED_count ??
      classificationData?.unclassified_materials ??
      0
    ),
  };

  // =========================================================
  // FILTER + SEARCH
  // =========================================================

  const filteredRows = normalizedRows.filter(
    (row) => {

      const search =
        resultSearch.trim().toLowerCase();

      const matchesSearch =
        !search ||
        String(row.materialCode)
          .toLowerCase()
          .includes(search) ||
        String(row.materialName)
          .toLowerCase()
          .includes(search) ||
        String(row.plant)
          .toLowerCase()
          .includes(search);

      const matchesFilter =
        resultFilter === "All" ||
        String(row.status).toLowerCase() ===
        resultFilter.toLowerCase();

      return (
        matchesSearch &&
        matchesFilter
      );
    }
  );


  // =========================================================
  // SORT
  // =========================================================

  const displayedRows = [
    ...filteredRows,
  ].sort((a, b) => {

    if (resultSort === "quantity-desc") {
      return (
        b.quantityChange -
        a.quantityChange
      );
    }

    if (resultSort === "quantity-asc") {
      return (
        a.quantityChange -
        b.quantityChange
      );
    }

    if (resultSort === "material") {
      return String(
        a.materialCode
      ).localeCompare(
        String(b.materialCode)
      );
    }

    return 0;
  });


  // =========================================================
  // WORKFLOW STATUS
  // =========================================================

  const workflowStatus =
    workflowResult?.status ||
    "idle";


  // =========================================================
  // RENDER
  // =========================================================

  return (

    <div className="app-shell">


      {/* ===================================================
          SIDEBAR
      =================================================== */}

      <aside className="sidebar">


        {/* BRAND */}

        <div className="brand">

          <div className="brand-icon">

            <BarChart3 size={23} />

          </div>


          <div>

            <h2>
              SapAi
            </h2>

            <span>
              BSP Automation
            </span>

          </div>

        </div>


        {/* MAIN NAVIGATION */}

        <div className="sidebar-section">

          <p className="sidebar-label">
            MAIN
          </p>


          <button
            className={
              activePage === "dashboard"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActivePage("dashboard")
            }
          >

            <Home size={18} />

            <span>
              Dashboard
            </span>

          </button>


          <button
            className={
              activePage === "automation"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActivePage("automation")
            }
          >

            <Play size={18} />

            <span>
              Automation
            </span>

          </button>


          <button
            className={
              activePage === "results"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActivePage("results")
            }
          >

            <TrendingUp size={18} />

            <span>
              Results
            </span>

          </button>

        </div>


        {/* SYSTEM */}

        <div className="sidebar-section">

          <p className="sidebar-label">
            SYSTEM
          </p>


          <button
            className="nav-item"
            onClick={() =>
              setActivePage("settings")
            }
          >

            <Settings size={18} />

            <span>
              Settings
            </span>

          </button>

        </div>


        {/* BACKEND STATUS */}

        <div className="sidebar-bottom">

          <div className="backend-card">

            <div
              className={
                backendStatus === "online"
                  ? "status-dot online"
                  : backendStatus === "checking"
                    ? "status-dot checking"
                    : "status-dot offline"
              }
            />


            <div>

              <strong>
                Backend
              </strong>


              <span>

                {backendStatus === "online"
                  ? "Connected"
                  : backendStatus === "checking"
                    ? "Checking..."
                    : "Offline"}

              </span>

            </div>

          </div>

        </div>

      </aside>


      {/* ===================================================
          MAIN CONTENT
      =================================================== */}

      <main className="main-content">


        {/* TOPBAR */}

        <header className="topbar">


          <div>

            <p className="eyebrow">
              BSP INVENTORY AUTOMATION
            </p>


            <h1>

              {activePage === "dashboard"
                ? "Inventory Dashboard"
                : activePage === "automation"
                  ? "Run Automation"
                  : activePage === "results"
                    ? "Inventory Results"
                    : "System Settings"}

            </h1>

          </div>


          <div className="topbar-actions">


            <button
              className="icon-button"
              onClick={checkBackend}
              title="Refresh backend status"
            >

              <RefreshCw
                size={18}
              />

            </button>


            <div className="user-chip">

              <div className="avatar">
                PJ
              </div>


              <div>

                <strong>
                  BSP User
                </strong>

                <span>
                  Inventory Analyst
                </span>

              </div>

            </div>

          </div>

        </header>


        {/* =================================================
            NOTIFICATION
        ================================================= */}

        {notification && (

          <div className="notification success">

            <CheckCircle2 size={18} />

            <span>
              {notification}
            </span>


            <button
              onClick={() =>
                setNotification("")
              }
            >

              <XCircle size={17} />

            </button>

          </div>

        )}


        {/* =================================================
            ERROR
        ================================================= */}

        {error && (

          <div className="notification error">

            <CircleAlert size={18} />

            <span>
              {error}
            </span>


            <button
              onClick={() =>
                setError("")
              }
            >

              <XCircle size={17} />

            </button>

          </div>

        )}


        {/* =================================================
            DASHBOARD
        ================================================= */}

        {activePage === "dashboard" && (

          <section className="page">


            {/* HERO */}

            <div className="hero-card">


              <div className="hero-content">


                <div className="hero-badge">

                  <Activity size={15} />

                  Deterministic Automation

                </div>


                <h2>
                  Automate your BSP inventory workflow.
                </h2>


                <p>
                  Process previous and current inventory,
                  compare changes, generate the report,
                  and validate the final workbook.
                </p>


                <button
                  className="primary-button"
                  onClick={() => setActivePage("automation")}
                  disabled={running}
                >

                  {running ? (

                    <>

                      <Loader2
                        size={18}
                        className="spin"
                      />

                      Running Workflow...

                    </>

                  ) : (

                    <>

                      <Play size={18} />

                      Run Inventory Automation

                    </>

                  )}

                </button>

              </div>


              <div className="hero-visual">

                <div className="visual-ring">

                  <FileSpreadsheet
                    size={48}
                  />

                </div>


                <div className="visual-line" />


                <div className="visual-node">
                  Compare
                </div>


                <div className="visual-line" />


                <div className="visual-node">
                  Report
                </div>

              </div>

            </div>


            {/* STATS */}

            <div className="stats-grid">


              <StatCard
                title="New Materials"
                value={newMaterials}
                icon={
                  <Upload size={20} />
                }
              />


              <StatCard
                title="Removed Materials"
                value={removedMaterials}
                icon={
                  <XCircle size={20} />
                }
              />


              <StatCard
                title="Existing Materials"
                value={existingMaterials}
                icon={
                  <RefreshCw size={20} />
                }
              />


              <StatCard
                title="Quantity Change"
                value={quantityChange}
                icon={
                  <TrendingUp size={20} />
                }
              />

            </div>


            {/* CONTENT GRID */}

            <div className="content-grid">


              {/* WORKFLOW */}

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <p className="panel-kicker">
                      WORKFLOW
                    </p>

                    <h3>
                      Automation Pipeline
                    </h3>

                  </div>


                  <ShieldCheck
                    size={22}
                  />

                </div>


                <WorkflowList
                  workflowResult={
                    workflowResult
                  }
                  getStepStatus={
                    getStepStatus
                  }
                />

              </div>


              {/* SYSTEM HEALTH */}

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <p className="panel-kicker">
                      SYSTEM
                    </p>

                    <h3>
                      System Health
                    </h3>

                  </div>


                  <Activity
                    size={22}
                  />

                </div>


                <div className="health-row">

                  <div className="health-icon">

                    <Activity
                      size={19}
                    />

                  </div>


                  <div>

                    <strong>
                      FastAPI Backend
                    </strong>

                    <span>

                      {backendStatus === "online"
                        ? "API is responding normally"
                        : backendStatus === "checking"
                          ? "Checking API connection..."
                          : "Backend connection unavailable"}

                    </span>

                  </div>


                  <div
                    className={
                      backendStatus === "online"
                        ? "health-status good"
                        : backendStatus === "checking"
                          ? "health-status"
                          : "health-status bad"
                    }
                  >

                    {backendStatus === "online"
                      ? "Online"
                      : backendStatus === "checking"
                        ? "Checking"
                        : "Offline"}

                  </div>

                </div>


                <div className="health-row">

                  <div className="health-icon">

                    <FileSpreadsheet
                      size={19}
                    />

                  </div>


                  <div>

                    <strong>
                      Inventory Engine
                    </strong>

                    <span>
                      Excel processing pipeline
                    </span>

                  </div>


                  <div className="health-status good">
                    Ready
                  </div>

                </div>


                <div className="health-row">

                  <div className="health-icon">

                    <ShieldCheck
                      size={19}
                    />

                  </div>


                  <div>

                    <strong>
                      Report Validation
                    </strong>

                    <span>
                      Generated reports are validated
                    </span>

                  </div>


                  <div className="health-status good">
                    Ready
                  </div>

                </div>

              </div>

            </div>

          </section>

        )}


        {/* =================================================
            AUTOMATION
        ================================================= */}

        {activePage === "automation" && (

          <section className="page">


            <div className="page-intro">

              <p className="panel-kicker">
                INVENTORY WORKFLOW
              </p>


              <h2>
                Run BSP Inventory Automation
              </h2>


              <p>
                Upload the two inventory workbooks, configure the
                reporting scope, and let the agent execute the
                deterministic BSP inventory workflow.
              </p>

            </div>


            <div className="automation-card automation-config-card">

              <div className="automation-card-header">
                <div className="automation-icon">
                  <FileSpreadsheet size={35} />
                </div>

                <div>
                  <p className="panel-kicker">WORKFLOW CONFIGURATION</p>
                  <h3>MC.1 Inventory Workflow</h3>
                  <p className="automation-muted">
                    Configure the reporting period and inventory scope before running the agent.
                  </p>
                </div>
              </div>

              <div className="inventory-upload-section">
                <div className="inventory-upload-header">
                  <div>
                    <p className="panel-kicker">INPUT FILES</p>
                    <h4>Upload Inventory Workbooks</h4>
                    <p>
                      Select the previous and current BSP inventory Excel files.
                      Both files are uploaded to the backend before the agent runs.
                    </p>
                  </div>
                  <span className="upload-required">2 files required</span>
                </div>

                <div className="inventory-upload-grid">
                  <label className={`inventory-file-box ${previousFile ? "has-file" : ""}`}>
                    <div className="inventory-file-icon">
                      <FileSpreadsheet size={25} />
                    </div>

                    <div className="inventory-file-content">
                      <strong>Previous Inventory</strong>
                      <span>Previous month / period workbook</span>
                      {previousFile ? (
                        <small title={previousFile.name}>{previousFile.name}</small>
                      ) : (
                        <small>No file selected</small>
                      )}
                    </div>

                    <span className="choose-file-button">
                      {previousFile ? "Change File" : "Choose File"}
                    </span>

                    <input
                      type="file"
                      accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                      onChange={(event) => setPreviousFile(event.target.files?.[0] || null)}
                      disabled={running || uploadingFiles}
                    />
                  </label>

                  <label className={`inventory-file-box ${currentFile ? "has-file" : ""}`}>
                    <div className="inventory-file-icon">
                      <FileSpreadsheet size={25} />
                    </div>

                    <div className="inventory-file-content">
                      <strong>Current Inventory</strong>
                      <span>Current month / period workbook</span>
                      {currentFile ? (
                        <small title={currentFile.name}>{currentFile.name}</small>
                      ) : (
                        <small>No file selected</small>
                      )}
                    </div>

                    <span className="choose-file-button">
                      {currentFile ? "Change File" : "Choose File"}
                    </span>

                    <input
                      type="file"
                      accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                      onChange={(event) => setCurrentFile(event.target.files?.[0] || null)}
                      disabled={running || uploadingFiles}
                    />
                  </label>
                </div>

                <div className="upload-status-row">
                  <span className={previousFile ? "file-ready" : "file-missing"}>
                    {previousFile ? "✓ Previous file ready" : "○ Previous file required"}
                  </span>
                  <span className={currentFile ? "file-ready" : "file-missing"}>
                    {currentFile ? "✓ Current file ready" : "○ Current file required"}
                  </span>
                </div>
              </div>

              <div className="automation-config-grid">

                <label className="automation-field">
                  <span>Previous Period</span>
                  <select
                    value={previousPeriod}
                    onChange={(e) => setPreviousPeriod(e.target.value)}
                    disabled={running}
                  >
                    <option>Previous Month</option>
                    <option>Previous Quarter</option>
                    <option>Previous Year</option>
                  </select>
                </label>

                <label className="automation-field">
                  <span>Current Period</span>
                  <select
                    value={currentPeriod}
                    onChange={(e) => setCurrentPeriod(e.target.value)}
                    disabled={running}
                  >
                    <option>Current Month</option>
                    <option>Current Quarter</option>
                    <option>Current Year</option>
                  </select>
                </label>

                <label className="automation-field">
                  <span>Plant</span>
                  <input
                    type="text"
                    value={selectedPlant}
                    onChange={(e) => setSelectedPlant(e.target.value.toUpperCase())}
                    placeholder="BSP"
                    disabled={running}
                  />
                </label>

                <label className="automation-field">
                  <span>Storage Location</span>
                  <select
                    value={storageLocation}
                    onChange={(e) => setStorageLocation(e.target.value)}
                    disabled={running}
                  >
                    <option>All</option>
                    <option>Configured</option>
                  </select>
                </label>

              </div>

              <div className="automation-fixed-config">
                <div>
                  <span>SAP Transaction</span>
                  <strong>MC.1</strong>
                </div>

                <div>
                  <span>Variant</span>
                  <strong>B002159</strong>
                </div>
              </div>

              <button
                className="primary-button large automation-run-button"
                onClick={runAutomation}
                disabled={
                  running ||
                  uploadingFiles ||
                  !previousFile ||
                  !currentFile
                }
              >
                {running || uploadingFiles ? (
                  <>
                    <Loader2 size={20} className="spin" />
                    {uploadingFiles
                      ? "Uploading Files..."
                      : "Processing Inventory..."}
                  </>
                ) : (
                  <>
                    <Play size={20} />
                    Run Agent
                  </>
                )}
              </button>

            </div>

            <div className="workflow-preview">

              <WorkflowList
                workflowResult={
                  workflowResult
                }
                getStepStatus={
                  getStepStatus
                }
              />

            </div>

          </section>

        )}


        {/* =================================================
            RESULTS
        ================================================= */}

        {activePage === "results" && (

          <section className="page">


            <div className="page-intro">

              <p className="panel-kicker">
                AUTOMATION OUTPUT
              </p>


              <h2>
                Inventory Comparison Results
              </h2>


              <p>
                Results from the latest completed
                inventory automation run.
              </p>

            </div>


            {!workflowResult ? (

              <div className="empty-state">

                <FileSpreadsheet
                  size={48}
                />


                <h3>
                  No automation run yet
                </h3>


                <p>
                  Run the inventory automation to generate
                  comparison results.
                </p>


                <button
                  className="primary-button"
                  onClick={() =>
                    setActivePage("automation")
                  }
                >

                  <Play size={18} />

                  Run Automation

                </button>

              </div>

            ) : (

              <>


                {/* RESULT STATS */}

                <div className="stats-grid">


                  <StatCard
                    title="New Materials"
                    value={newMaterials}
                    icon={
                      <Upload size={20} />
                    }
                  />


                  <StatCard
                    title="Removed Materials"
                    value={removedMaterials}
                    icon={
                      <XCircle size={20} />
                    }
                  />


                  <StatCard
                    title="Existing Materials"
                    value={existingMaterials}
                    icon={
                      <RefreshCw size={20} />
                    }
                  />


                  <StatCard
                    title="Quantity Change"
                    value={quantityChange}
                    icon={
                      <TrendingUp size={20} />
                    }
                  />

                </div>
{/* =========================================================
    AI INVENTORY ANALYSIS
========================================================= */}

                {inventoryAnalysis && (
                  <div className="ai-analysis-panel">

                    <div className="panel-header">
                      <div>
                        <p className="panel-kicker">
                          AI INVENTORY ANALYSIS
                        </p>

                        <h3>
                          Inventory Intelligence
                        </h3>

                        <span className="results-count">
                          Automated interpretation of inventory changes
                        </span>
                      </div>

                      <div
                        className={`analysis-risk ${String(
                          analysisRisk
                        ).toLowerCase()}`}
                      >
                        {analysisRisk}
                      </div>
                    </div>

                    {/* ANALYSIS STATS */}

                    <div className="analysis-stats">

                      <div className="analysis-stat">
                        <span>Significant Changes</span>
                        <strong>
                          {significantChangeCount}
                        </strong>
                      </div>

                      <div className="analysis-stat">
                        <span>Zero Stock Materials</span>
                        <strong>
                          {zeroStockMaterials}
                        </strong>
                      </div>

                      <div className="analysis-stat">
                        <span>Top Increases</span>
                        <strong>
                          {Array.isArray(topIncreases)
                            ? topIncreases.length
                            : 0}
                        </strong>
                      </div>

                      <div className="analysis-stat">
                        <span>Top Decreases</span>
                        <strong>
                          {Array.isArray(topDecreases)
                            ? topDecreases.length
                            : 0}
                        </strong>
                      </div>

                    </div>

                    {/* RECOMMENDATIONS */}

                    {Array.isArray(recommendations) &&
                      recommendations.length > 0 && (

                        <div className="analysis-section">

                          <div className="analysis-section-title">
                            <ShieldCheck size={17} />

                            <strong>
                              Recommendations
                            </strong>
                          </div>

                          <div className="recommendation-list">

                            {recommendations
                              .slice(0, 5)
                              .map((recommendation, index) => (

                                <div
                                  className="recommendation-item"
                                  key={index}
                                >
                                  <span className="recommendation-number">
                                    {index + 1}
                                  </span>

                                  <span>
                                    {typeof recommendation === "string"
                                      ? recommendation
                                      : recommendation?.message ||
                                      recommendation?.recommendation ||
                                      JSON.stringify(
                                        recommendation
                                      )}
                                  </span>
                                </div>

                              ))}

                          </div>

                        </div>

                      )}

                    {/* SIGNIFICANT CHANGES */}

                    {Array.isArray(significantChanges) &&
                      significantChanges.length > 0 && (

                        <div className="analysis-section">

                          <div className="analysis-section-title">
                            <TrendingUp size={17} />

                            <strong>
                              Significant Inventory Changes
                            </strong>
                          </div>

                          <div className="analysis-change-list">

                            {significantChanges
                              .slice(0, 5)
                              .map((change, index) => (

                                <div
                                  className="analysis-change-item"
                                  key={index}
                                >

                                  <div>
                                    <strong>
                                      {change?.Material_Code ||
                                        change?.material_code ||
                                        change?.material ||
                                        "Material"}
                                    </strong>

                                    <span>
                                      {change?.Material_Name ||
                                        change?.material_name ||
                                        change?.name ||
                                        "Inventory change detected"}
                                    </span>
                                  </div>

                                  <strong>
                                    {change?.change_percent !==
                                      undefined &&
                                      change?.change_percent !== null
                                      ? `${Number(
                                        change.change_percent
                                      ).toFixed(1)}%`
                                      : change?.percentage_change !==
                                        undefined &&
                                        change?.percentage_change !== null
                                        ? `${Number(
                                          change.percentage_change
                                        ).toFixed(1)}%`
                                        : change?.Quantity_Change !==
                                          undefined
                                          ? Number(
                                            change.Quantity_Change
                                          ).toLocaleString()
                                          : change?.quantity_change !==
                                            undefined
                                            ? Number(
                                              change.quantity_change
                                            ).toLocaleString()
                                            : "Change detected"}
                                  </strong>

                                </div>

                              ))}

                          </div>

                        </div>

                      )}

                  </div>
                )}

                {/* =========================================================
                    RI / CAPITAL CLASSIFICATION
                ========================================================= */}

                {classificationResult && (
                  <div className="results-panel classification-panel">
                    <div className="panel-header">
                      <div>
                        <p className="panel-kicker">
                          MATERIAL CLASSIFICATION
                        </p>

                        <h3>
                          RI / Capital Classification
                        </h3>

                        <span className="results-count">
                          Deterministic classification using exact material-code
                          reference matching
                        </span>
                      </div>

                      <ShieldCheck size={28} />
                    </div>

                    {!classificationReferencesAvailable && (
                      <div className="result-warning classification-warning">
                        <CircleAlert size={22} />

                        <div>
                          <strong>
                            RI / Capital reference files are not available.
                          </strong>

                          <span>
                            Materials are shown as UNCLASSIFIED rather than
                            being guessed or automatically assigned.
                          </span>
                        </div>
                      </div>
                    )}

                    {classificationReferencesAvailable &&
                      classificationWarnings.length > 0 && (
                        <div className="result-warning classification-warning">
                          <CircleAlert size={22} />

                          <div>
                            <strong>Classification warnings</strong>

                            <span>
                              {classificationWarnings
                                .slice(0, 3)
                                .map((warning, index) => (
                                  <span key={index}>
                                    {typeof warning === "string"
                                      ? warning
                                      : warning?.message ||
                                        JSON.stringify(warning)}
                                    {index <
                                    Math.min(
                                      classificationWarnings.length,
                                      3
                                    ) -
                                      1
                                      ? " "
                                      : ""}
                                  </span>
                                ))}
                            </span>
                          </div>
                        </div>
                      )}

                    <div className="stats-grid classification-stats">
                      <StatCard
                        title="RI Materials"
                        value={classificationCounts.ri}
                        icon={<ShieldCheck size={20} />}
                      />

                      <StatCard
                        title="Capital Materials"
                        value={classificationCounts.capital}
                        icon={<BarChart3 size={20} />}
                      />

                      <StatCard
                        title="Normal Materials"
                        value={classificationCounts.normal}
                        icon={<CheckCircle2 size={20} />}
                      />

                      <StatCard
                        title="Unclassified"
                        value={classificationCounts.unclassified}
                        icon={<CircleAlert size={20} />}
                      />
                    </div>

                    {classificationRows.length > 0 && (
                      <div className="table-wrapper classification-table-wrapper">
                        <table className="inventory-table classification-table">
                          <thead>
                            <tr>
                              <th>Material</th>
                              <th>Material Name</th>
                              <th>Inventory Type</th>
                              <th>Classification Reason</th>
                            </tr>
                          </thead>

                          <tbody>
                            {classificationRows.map((row) => {
                              const type =
                                String(row.inventoryType).toUpperCase();

                              const typeClass =
                                type === "RI"
                                  ? "ri"
                                  : type === "CAPITAL"
                                    ? "capital"
                                    : type === "NORMAL"
                                      ? "normal"
                                      : "unclassified";

                              return (
                                <tr key={row.id}>
                                  <td>
                                    <strong className="material-code">
                                      {row.materialCode}
                                    </strong>
                                  </td>

                                  <td>
                                    <span className="material-name">
                                      {row.materialName}
                                    </span>
                                  </td>

                                  <td>
                                    <span
                                      className={`status-badge classification-badge ${typeClass}`}
                                    >
                                      {type}
                                    </span>
                                  </td>

                                  <td>
                                    {row.classificationReason}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* INTERACTIVE COMPARISON TABLE */}

                <div className="results-table-panel">
                    <div className="results-table-header">
                      <div>
                        <p className="panel-kicker">MATERIAL ANALYSIS</p>
                        <h3>Inventory Changes</h3>
                        <span className="results-count">
                          Showing {displayedRows.length} of {normalizedRows.length} materials
                        </span>
                      </div>

                      <div className="table-controls">
                        <div className="search-box">
                          <Search size={17} />
                          <input
                            type="text"
                            placeholder="Search material, name or plant..."
                            value={resultSearch}
                            onChange={(event) => setResultSearch(event.target.value)}
                          />
                        </div>

                        <div className="filter-box">
                          <Filter size={16} />
                          <select
                            value={resultFilter}
                            onChange={(event) => setResultFilter(event.target.value)}
                          >
                            <option value="All">All Status</option>
                            <option value="New">New</option>
                            <option value="Existing">Existing</option>
                            <option value="Removed">Removed</option>
                          </select>
                        </div>

                        <div className="filter-box">
                          <ArrowUpDown size={16} />
                          <select
                            value={resultSort}
                            onChange={(event) => setResultSort(event.target.value)}
                          >
                            <option value="none">Default Order</option>
                            <option value="material">Material Code</option>
                            <option value="quantity-desc">Quantity Change ↓</option>
                            <option value="quantity-asc">Quantity Change ↑</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    {displayedRows.length === 0 ? (
                      <div className="table-empty">
                        <Search size={32} />
                        <h4>No materials found</h4>
                        <p>Try changing your search or status filter.</p>
                      </div>
                    ) : (
                      <div className="table-wrapper">
                        <table className="inventory-table">
                          <thead>
                            <tr>
                              <th>Material</th>
                              <th>Material Name</th>
                              <th>Previous Qty</th>
                              <th>Current Qty</th>
                              <th>Change</th>
                              <th>Unit</th>
                              <th>Plant</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {displayedRows.map((row) => {
                              const change = row.quantityChange;
                              const status = String(row.status).toLowerCase();
                              return (
                                <tr key={row.id}>
                                  <td><strong className="material-code">{row.materialCode}</strong></td>
                                  <td><span className="material-name">{row.materialName}</span></td>
                                  <td>{row.previousQuantity.toLocaleString()}</td>
                                  <td>{row.currentQuantity.toLocaleString()}</td>
                                  <td>
                                    <span className={change > 0 ? "quantity-change positive" : change < 0 ? "quantity-change negative" : "quantity-change neutral"}>
                                      {change > 0 ? "+" : ""}{change.toLocaleString()}
                                    </span>
                                  </td>
                                  <td>{row.unit}</td>
                                  <td>{row.plant}</td>
                                  <td><span className={`status-badge ${status}`}>{row.status}</span></td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                </div>

                {/* RESULT PANEL */}

                <div className="results-panel">


                    <div className="panel-header">

                      <div>

                        <p className="panel-kicker">
                          STATUS
                        </p>


                        <h3>

                          {workflowStatus ===
                            "completed"
                            ? "Workflow Completed"
                            : "Workflow Result"}

                        </h3>

                      </div>


                      <CheckCircle2
                        size={28}
                      />

                    </div>


                    <div className={
                      workflowStatus === "completed"
                        ? "result-success"
                        : "result-warning"
                    }>

                      {workflowStatus === "completed" ? (
                        <CheckCircle2 size={24} />
                      ) : (
                        <CircleAlert size={24} />
                      )}

                      <div>

                        <strong>
                          {workflowStatus === "completed"
                            ? "Inventory report generated and validated successfully."
                            : "Inventory workflow did not complete successfully."}
                        </strong>

                        <span>
                          {workflowStatus === "completed"
                            ? "All workflow stages completed."
                            : "Check the workflow steps above for the failed stage."}
                        </span>

                      </div>

                    </div>


                    <button
                      className="primary-button"
                      onClick={downloadReport}
                    >

                      <Download size={19} />

                      Download BSP Inventory Report

                    </button>

                  </div>


                  {/* EXECUTION DETAILS */}

                  <div className="panel">

                    <div className="panel-header">

                      <div>

                        <p className="panel-kicker">
                          EXECUTION DETAILS
                        </p>


                        <h3>
                          Workflow Steps
                        </h3>

                      </div>

                    </div>


                    <WorkflowList
                      workflowResult={
                        workflowResult
                      }
                      getStepStatus={
                        getStepStatus
                      }
                    />

                  </div>

                </>

            )}

              </section>

        )}


            {/* =================================================
            SETTINGS
        ================================================= */}

            {activePage === "settings" && (

              <section className="page">


                <div className="page-intro">

                  <p className="panel-kicker">
                    CONFIGURATION
                  </p>


                  <h2>
                    System Settings
                  </h2>


                  <p>
                    Current BSP inventory automation configuration.
                  </p>

                </div>


                <div className="settings-grid">


                  <Setting
                    label="API Server"
                    value={API_BASE_URL}
                  />


                  <Setting
                    label="SAP Transaction"
                    value="MC.1"
                  />


                  <Setting
                    label="SAP Variant"
                    value="B002159"
                  />


                  <Setting
                    label="Plant"
                    value="BSP"
                  />


                  <Setting
                    label="Previous Inventory"
                    value="previous_inventory.xlsx"
                  />


                  <Setting
                    label="Current Inventory"
                    value="current_inventory.xlsx"
                  />


                  <Setting
                    label="Report"
                    value="BSP_Inventory_Report.xlsx"
                  />

                </div>

              </section>

            )}

          </main>

    </div>
  );
}


// =========================================================
// STAT CARD
// =========================================================

function StatCard({
  title,
  value,
  icon,
}) {

  return (

    <div className="stat-card">

      <div className="stat-icon">
        {icon}
      </div>


      <div>

        <span>
          {title}
        </span>


        <strong>
          {value}
        </strong>

      </div>

    </div>
  );
}


// =========================================================
// WORKFLOW LIST
// =========================================================

function WorkflowList({
  workflowResult,
  getStepStatus,
}) {

  return (

    <div className="workflow-list">

      {WORKFLOW_STEPS.map(
        (stepName, index) => {

          const status =
            workflowResult
              ? getStepStatus(stepName)
              : "pending";


          return (

            <div
              className="workflow-item"
              key={stepName}
            >


              <div className="workflow-number">

                {status === "completed" ? (

                  <CheckCircle2
                    size={21}
                  />

                ) : status === "failed" ? (

                  <XCircle
                    size={21}
                  />

                ) : status === "running" ? (

                  <Loader2
                    size={21}
                    className="spin"
                  />

                ) : (

                  index + 1

                )}

              </div>


              <div className="workflow-info">

                <strong>
                  {stepName}
                </strong>


                <span>

                  {status === "completed"
                    ? "Completed successfully"
                    : status === "running"
                      ? "Currently running"
                      : status === "failed"
                        ? "Step failed"
                        : "Waiting"}

                </span>

              </div>


              <div
                className={
                  `workflow-status ${status}`
                }
              >

                {status}

              </div>

            </div>

          );

        }
      )}

    </div>
  );
}


// =========================================================
// SETTING
// =========================================================

function Setting({
  label,
  value,
}) {

  return (

    <div className="setting-card">

      <span>
        {label}
      </span>


      <strong>
        {value}
      </strong>

    </div>
  );
}


// =========================================================
// EXPORT
// =========================================================

export default App;