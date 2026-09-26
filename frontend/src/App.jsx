import { useEffect, useMemo, useRef, useState } from "react";

import {
  Activity,
  ArrowUpDown,
  BarChart3,
  CheckCircle2,
  CircleAlert,
  Download,
  FileSpreadsheet,
  Filter,
  Home,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  TrendingUp,
  Upload,
  XCircle,
} from "lucide-react";

import "./App.css";


// ============================================================
// API CONFIGURATION
// ============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";


// ============================================================
// WORKFLOW
// ============================================================

const WORKFLOW_STEPS = [
  "Process MC.1 Raw Data",
  "Build BSP Inventory Workbook",
  "Update mminv_new",
  "Run ZMAT-FUND_POPR",
  "Extract Spool and Build Inventory PO",
  "Update mminv1_new",
];


// ============================================================
// HELPERS
// ============================================================

function getErrorMessage(error) {
  if (!error) {
    return "Unknown error.";
  }

  if (typeof error === "string") {
    return error;
  }

  return (
    error.message ||
    error.detail ||
    error.error ||
    "Something went wrong."
  );
}


function formatNumber(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "0";
  }

  return number.toLocaleString();
}


function normalizeStatus(status) {
  return String(status || "")
    .trim()
    .toLowerCase();
}


function getNestedValue(object, paths, fallback = null) {
  for (const path of paths) {
    const parts = path.split(".");

    let value = object;

    for (const part of parts) {
      if (
        value === null ||
        value === undefined
      ) {
        break;
      }

      value = value[part];
    }

    if (
      value !== undefined &&
      value !== null
    ) {
      return value;
    }
  }

  return fallback;
}


// ============================================================
// MAIN APP
// ============================================================

function App() {

  // ==========================================================
  // PAGE
  // ==========================================================

  const [activePage, setActivePage] =
    useState("dashboard");


  // ==========================================================
  // BACKEND
  // ==========================================================

  const [backendStatus, setBackendStatus] = useState("checking");


  // ==========================================================
  // FILES
  // ==========================================================

  const [previousFile, setPreviousFile] =
    useState(null);

  const [currentFile, setCurrentFile] =
    useState(null);


  // ==========================================================
  // CONFIG
  // ==========================================================

  const [previousPeriod, setPreviousPeriod] =
    useState("Previous Month");

  const [currentPeriod, setCurrentPeriod] =
    useState("Current Month");

  const [selectedPlant, setSelectedPlant] =
    useState("1000");

  const [storageLocation, setStorageLocation] =
    useState("All");


  // ==========================================================
  // RUN STATE
  // ==========================================================

  const [running, setRunning] =
    useState(false);

  const [runningStep, setRunningStep] =
    useState(-1);

  const [runId, setRunId] =
    useState(null);

  const [workflowResult, setWorkflowResult] =
    useState(null);


  // ==========================================================
  // UI
  // ==========================================================

  const [error, setError] =
    useState("");

  const [notification, setNotification] =
    useState("");

  const [uploadProgress, setUploadProgress] =
    useState(0);


  // ==========================================================
  // RESULTS
  // ==========================================================

  const [resultSearch, setResultSearch] =
    useState("");

  const [resultFilter, setResultFilter] =
    useState("All");

  const [resultSort, setResultSort] =
    useState("none");


  // ==========================================================
  // POLLING REF
  // ==========================================================

  const pollTimerRef =
    useRef(null);


  // ==========================================================
  // CLEANUP
  // ==========================================================

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, []);


  // ==========================================================
  // BACKEND HEALTH
  // ==========================================================

  const checkBackend = async () => {

    setBackendStatus("checking");

    try {

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


  // ==========================================================
  // INITIAL HEALTH CHECK
  // ==========================================================

  useEffect(() => {

  const initialCheck = setTimeout(() => {
    checkBackend();
  }, 0);

  const interval = setInterval(
    checkBackend,
    10000
  );

  return () => {
    clearTimeout(initialCheck);
    clearInterval(interval);
  };

}, []);


  // ==========================================================
  // RESPONSE PARSER
  // ==========================================================

  const parseResponse = async (response) => {

    const contentType =
      response.headers.get(
        "content-type"
      ) || "";


    if (
      contentType.includes(
        "application/json"
      )
    ) {

      try {
        return await response.json();
      } catch {
        return {};
      }
    }


    const text =
      await response.text();


    return {
      detail: text,
    };
  };


  // ==========================================================
  // VALIDATE FILE
  // ==========================================================

  const validateExcelFile = (
    file,
    label
  ) => {

    if (!file) {
      throw new Error(
        `${label} file is required.`
      );
    }


    const validExtensions = [
      ".xlsx",
      ".xls",
    ];


    const name =
      file.name.toLowerCase();


    const valid =
      validExtensions.some(
        (extension) =>
          name.endsWith(extension)
      );


    if (!valid) {
      throw new Error(
        `${label} must be an Excel file (.xlsx or .xls).`
      );
    }


    return true;
  };


  // ==========================================================
  // RESET RUN
  // ==========================================================

  const resetRun = () => {

    if (pollTimerRef.current) {
      clearTimeout(
        pollTimerRef.current
      );
    }

    setRunning(false);
    setRunningStep(-1);
    setRunId(null);
    setWorkflowResult(null);
    setUploadProgress(0);
    setError("");
    setNotification("");
  };


  // ==========================================================
  // GET CURRENT STEP
  // ==========================================================

  const getStepIndex = (
    currentStep
  ) => {

    if (!currentStep) {
      return -1;
    }


    const text =
      String(currentStep)
        .toLowerCase();


    const index =
      WORKFLOW_STEPS.findIndex(
        (step) =>
          step
            .toLowerCase()
            .includes(text) ||
          text.includes(
            step.toLowerCase()
          )
      );


    return index;
  };


  // ==========================================================
  // POLL BSP STATUS
  // ==========================================================

  const pollBspStatus = async (
    currentRunId
  ) => {

    try {

      const response =
        await fetch(
          `${API_BASE_URL}/bsp/status/${currentRunId}`,
          {
            method: "GET",
            headers: {
              Accept:
                "application/json",
            },
          }
        );


      const data =
        await parseResponse(
          response
        );


      if (!response.ok) {
        throw new Error(
          data?.detail ||
          data?.message ||
          `Unable to read BSP status. HTTP ${response.status}`
        );
      }


      setWorkflowResult(data);


      const currentStep =
        getNestedValue(
          data,
          [
            "current_step",
            "currentStep",
            "step",
            "current_stage",
            "currentStage",
          ],
          ""
        );


      const index =
        getStepIndex(
          currentStep
        );


      if (index >= 0) {
        setRunningStep(index);
      }


      const status =
        normalizeStatus(
          data?.status
        );


      // --------------------------------------------------------
      // SUCCESS
      // --------------------------------------------------------

      if (
        [
          "completed",
          "complete",
          "success",
          "successful",
          "done",
        ].includes(status)
      ) {

        setRunningStep(
          WORKFLOW_STEPS.length
        );

        setRunning(false);

        setNotification(
          "Inventory automation completed successfully."
        );

        setActivePage(
          "results"
        );

        return;
      }


      // --------------------------------------------------------
      // FAILURE
      // --------------------------------------------------------

      if (
        [
          "failed",
          "failure",
          "error",
        ].includes(status)
      ) {

        setRunning(false);

        const errors =
          Array.isArray(
            data?.errors
          )
            ? data.errors
            : [];


        const lastError =
          errors.length
            ? errors[
                errors.length - 1
              ]
            : null;


        setError(
          typeof lastError ===
          "string"
            ? lastError
            : lastError?.message ||
              data?.error ||
              data?.detail ||
              "BSP automation failed."
        );

        return;
      }


      // --------------------------------------------------------
      // CONTINUE POLLING
      // --------------------------------------------------------

      pollTimerRef.current =
        setTimeout(
          () =>
            pollBspStatus(
              currentRunId
            ),
          1000
        );

    } catch (err) {

      console.error(
        "BSP status polling failed:",
        err
      );

      setRunning(false);

      setError(
        getErrorMessage(err)
      );
    }
  };


  // ==========================================================
  // RUN BSP AUTOMATION
  // ==========================================================

  const runAutomation = async () => {

    if (running) {
      return;
    }


    setError("");
    setNotification("");
    setWorkflowResult(null);
    setRunId(null);
    setRunningStep(0);
    setUploadProgress(0);


    // --------------------------------------------------------
    // VALIDATION
    // --------------------------------------------------------

    try {

      validateExcelFile(
        previousFile,
        "Previous inventory"
      );

      validateExcelFile(
        currentFile,
        "Current inventory"
      );

    } catch (err) {

      setError(
        getErrorMessage(err)
      );

      setActivePage(
        "automation"
      );

      return;
    }


    // --------------------------------------------------------
    // BACKEND CHECK
    // --------------------------------------------------------

    if (
      backendStatus !==
      "online"
    ) {

      await checkBackend();

      // Give the state a moment to update.
      // The actual request below will still
      // be the final source of truth.
    }


    setRunning(true);


    try {

      // ------------------------------------------------------
      // FORM DATA
      // ------------------------------------------------------

      const formData =
        new FormData();


      formData.append(
        "previous_file",
        previousFile
      );


      formData.append(
        "current_file",
        currentFile
      );


      formData.append(
        "mode",
        "offline"
      );


      formData.append(
        "plant",
        selectedPlant
      );


      formData.append(
        "previous_period",
        previousPeriod
      );


      formData.append(
        "current_period",
        currentPeriod
      );


      formData.append(
        "storage_location",
        storageLocation
      );


      // ------------------------------------------------------
      // UI
      // ------------------------------------------------------

      setNotification(
        "Uploading Previous and Current raw MC.1 files..."
      );


      setUploadProgress(20);


      // ------------------------------------------------------
      // REAL BSP ENDPOINT
      // ------------------------------------------------------

      const response =
        await fetch(
          `${API_BASE_URL}/bsp/run`,
          {
            method: "POST",
            body: formData,
          }
        );


      setUploadProgress(70);


      const data =
        await parseResponse(
          response
        );


      console.log(
        "BSP /run response:",
        data
      );


      if (!response.ok) {

        throw new Error(
          data?.detail ||
          data?.message ||
          data?.error ||
          `BSP automation failed with HTTP ${response.status}`
        );
      }


      setUploadProgress(100);


      // ------------------------------------------------------
      // RUN ID
      // ------------------------------------------------------

      const returnedRunId =
        data?.run_id ||
        data?.runId ||
        data?.id;


      if (!returnedRunId) {

        // Some implementations may
        // execute synchronously.

        if (
          [
            "completed",
            "complete",
            "success",
          ].includes(
            normalizeStatus(
              data?.status
            )
          )
        ) {

          setWorkflowResult(
            data
          );

          setRunningStep(
            WORKFLOW_STEPS.length
          );

          setRunning(false);

          setNotification(
            "Inventory automation completed successfully."
          );

          setActivePage(
            "results"
          );

          return;
        }


        throw new Error(
          "Backend did not return a BSP run ID."
        );
      }


      setRunId(
        returnedRunId
      );


      setNotification(
        "Automation started. Processing raw MC.1 data..."
      );


      // ------------------------------------------------------
      // START STATUS POLLING
      // ------------------------------------------------------

      setRunningStep(0);


      pollBspStatus(
        returnedRunId
      );

    } catch (err) {

      console.error(
        "BSP automation failed:",
        err
      );

      setRunning(false);

      setUploadProgress(0);

      setError(
        getErrorMessage(err)
      );
    }
  };


  // ==========================================================
  // DOWNLOAD BSP FILE
  // ==========================================================

  const downloadBspFile = async (
    filename = "BSP_Inventory.xlsx"
  ) => {

    if (!runId) {

      setError(
        "No completed BSP run is available."
      );

      return;
    }


    try {

      setError("");

      setNotification(
        `Preparing ${filename}...`
      );


      const response =
        await fetch(
          `${API_BASE_URL}/bsp/files/${encodeURIComponent(
            runId
          )}/${encodeURIComponent(
            filename
          )}`,
          {
            method: "GET",
          }
        );


      if (!response.ok) {

        const data =
          await parseResponse(
            response
          );


        throw new Error(
          data?.detail ||
          data?.message ||
          `File download failed with HTTP ${response.status}`
        );
      }


      const blob =
        await response.blob();


      const url =
        window.URL.createObjectURL(
          blob
        );


      const link =
        document.createElement(
          "a"
        );


      link.href = url;

      link.download =
        filename;


      document.body.appendChild(
        link
      );


      link.click();


      link.remove();


      window.URL.revokeObjectURL(
        url
      );


      setNotification(
        `${filename} downloaded successfully.`
      );

    } catch (err) {

      console.error(
        "BSP file download failed:",
        err
      );


      setError(
        getErrorMessage(err)
      );
    }
  };


  // ==========================================================
  // WORKFLOW STEPS
  // ==========================================================

  const backendSteps =
    Array.isArray(
      workflowResult?.steps
    )
      ? workflowResult.steps
      : [];


  const getStepStatus = (
    stepName
  ) => {

    // --------------------------------------------------------
    // BACKEND RESULT
    // --------------------------------------------------------

    if (
      backendSteps.length
    ) {

      const backendStep =
        backendSteps.find(
          (step) => {

            const name =
              String(
                step?.step ||
                step?.name ||
                step?.stage ||
                ""
              ).toLowerCase();


            return (
              name ===
                stepName.toLowerCase() ||
              name.includes(
                stepName.toLowerCase()
              ) ||
              stepName
                .toLowerCase()
                .includes(name)
            );
          }
        );


      if (backendStep) {

        const status =
          normalizeStatus(
            backendStep.status
          );


        if (
          [
            "completed",
            "complete",
            "success",
            "successful",
            "done",
          ].includes(status)
        ) {
          return "completed";
        }


        if (
          [
            "failed",
            "failure",
            "error",
          ].includes(status)
        ) {
          return "failed";
        }


        if (
          [
            "running",
            "processing",
            "in_progress",
            "in-progress",
          ].includes(status)
        ) {
          return "running";
        }
      }
    }


    // --------------------------------------------------------
    // VISUAL FALLBACK
    // --------------------------------------------------------

    if (running) {

      const index =
        WORKFLOW_STEPS.indexOf(
          stepName
        );


      if (
        index <
        runningStep
      ) {
        return "completed";
      }


      if (
        index ===
        runningStep
      ) {
        return "running";
      }


      return "pending";
    }


    return "pending";
  };


  // ==========================================================
  // COMPARISON RESULT
  // ==========================================================

  const comparisonResult =
    workflowResult?.comparison_result ||
    workflowResult?.results?.comparison ||
    null;


  const comparisonSummary =
    comparisonResult?.summary ||
    workflowResult?.results?.comparison?.summary ||
    {};


  const newMaterials =
    Number(
      comparisonSummary?.new_materials ??
      comparisonSummary?.newMaterials ??
      0
    );


  const removedMaterials =
    Number(
      comparisonSummary?.removed_materials ??
      comparisonSummary?.removedMaterials ??
      0
    );


  const existingMaterials =
    Number(
      comparisonSummary?.existing_materials ??
      comparisonSummary?.existingMaterials ??
      0
    );


  const quantityChange =
    Number(
      comparisonSummary?.total_quantity_change ??
      comparisonSummary?.totalQuantityChange ??
      0
    );


  // ==========================================================
  // AI ANALYSIS
  // ==========================================================

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
    Array.isArray(
      analysisData?.significant_changes
    )
      ? analysisData.significant_changes
      : [];


  const topIncreases =
    Array.isArray(
      analysisData?.top_increases
    )
      ? analysisData.top_increases
      : [];


  const topDecreases =
    Array.isArray(
      analysisData?.top_decreases
    )
      ? analysisData.top_decreases
      : [];


  const recommendations =
    Array.isArray(
      analysisData?.recommendations
    )
      ? analysisData.recommendations
      : [];


  const zeroStockMaterials =
    Number(
      analysisData?.zero_stock_materials_count ??
      (
        Array.isArray(
          analysisData?.zero_stock_materials
        )
          ? analysisData.zero_stock_materials.length
          : analysisData?.zero_stock_materials
      ) ??
      analysisData?.zero_stock ??
      0
    );


  // ==========================================================
  // COMPARISON ROWS
  // ==========================================================

  const comparisonRows =
    Array.isArray(
      comparisonResult?.comparison
    )
      ? comparisonResult.comparison
      : Array.isArray(
          workflowResult?.results?.comparison?.comparison
        )
        ? workflowResult.results.comparison.comparison
        : [];


  const normalizedRows =
    comparisonRows.map(
      (row, index) => {

        const previousQuantity =
          Number(
            row?.Previous_Quantity ??
            row?.previous_quantity ??
            row?.["Previous Quantity"] ??
            row?.previous_qty ??
            0
          );


        const currentQuantity =
          Number(
            row?.Current_Quantity ??
            row?.current_quantity ??
            row?.["Current Quantity"] ??
            row?.current_qty ??
            0
          );


        const quantityChangeValue =
          Number(
            row?.Quantity_Change ??
            row?.quantity_change ??
            row?.["Quantity Change"] ??
            row?.change ??
            currentQuantity -
              previousQuantity
          );


        return {

          id: index,

          materialCode:
            row?.Material_Code ??
            row?.material_code ??
            row?.["Material Code"] ??
            row?.material ??
            "-",

          materialName:
            row?.Material_Name ??
            row?.material_name ??
            row?.["Material Name"] ??
            row?.name ??
            "-",

          previousQuantity,

          currentQuantity,

          quantityChange:
            quantityChangeValue,

          unit:
            row?.Unit ??
            row?.unit ??
            "-",

          plant:
            row?.Plant ??
            row?.plant ??
            "-",

          status:
            row?.Status ??
            row?.status ??
            "Existing",

          inventoryKey:
            row?.Inventory_Key ??
            row?.inventory_key ??
            row?.["Inventory Key"] ??
            "-",
        };
      }
    );


  // ==========================================================
  // CLASSIFICATION
  // ==========================================================

  const classificationResult =
    workflowResult?.metadata?.inventory_classification ||
    workflowResult?.results?.classification ||
    null;


  const classificationData =
    classificationResult?.classification ||
    classificationResult?.data ||
    {};


  const classificationRowsRaw =
    Array.isArray(
      classificationResult?.comparison
    )
      ? classificationResult.comparison
      : Array.isArray(
          classificationResult?.results
        )
        ? classificationResult.results
        : [];


  const classificationRows =
    classificationRowsRaw.map(
      (row, index) => ({

        id:
          `classification-${index}`,

        materialCode:
          row?.Material_Code ??
          row?.material_code ??
          row?.["Material Code"] ??
          row?.material ??
          "-",

        materialName:
          row?.Material_Name ??
          row?.material_name ??
          row?.["Material Name"] ??
          row?.name ??
          "-",

        inventoryType:
          row?.Inventory_Type ??
          row?.inventory_type ??
          row?.["Inventory Type"] ??
          row?.classification ??
          "UNCLASSIFIED",

        classificationReason:
          row?.Classification_Reason ??
          row?.classification_reason ??
          row?.["Classification Reason"] ??
          row?.reason ??
          "-",
      })
    );


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


  // ==========================================================
  // SEARCH / FILTER / SORT
  // ==========================================================

  const displayedRows =
    useMemo(() => {

      const search =
        resultSearch
          .trim()
          .toLowerCase();


      let rows =
        normalizedRows.filter(
          (row) => {

            const matchesSearch =
              !search ||
              String(
                row.materialCode
              )
                .toLowerCase()
                .includes(search) ||
              String(
                row.materialName
              )
                .toLowerCase()
                .includes(search) ||
              String(
                row.plant
              )
                .toLowerCase()
                .includes(search);


            const matchesFilter =
              resultFilter ===
                "All" ||
              String(
                row.status
              ).toLowerCase() ===
                resultFilter.toLowerCase();


            return (
              matchesSearch &&
              matchesFilter
            );
          }
        );


      rows = [
        ...rows,
      ].sort(
        (a, b) => {

          if (
            resultSort ===
            "quantity-desc"
          ) {
            return (
              b.quantityChange -
              a.quantityChange
            );
          }


          if (
            resultSort ===
            "quantity-asc"
          ) {
            return (
              a.quantityChange -
              b.quantityChange
            );
          }


          if (
            resultSort ===
            "material"
          ) {
            return String(
              a.materialCode
            ).localeCompare(
              String(
                b.materialCode
              )
            );
          }


          return 0;
        }
      );


      return rows;

    }, [
      normalizedRows,
      resultSearch,
      resultFilter,
      resultSort,
    ]);


  // ==========================================================
  // WORKFLOW STATUS
  // ==========================================================

  const workflowStatus =
    normalizeStatus(
      workflowResult?.status
    ) || "idle";


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="app-shell">

      {/* ====================================================
          SIDEBAR
      ==================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            <BarChart3 size={23} />
          </div>

          <div>
            <h2>SapAi</h2>
            <span>BSP Automation</span>
          </div>

        </div>


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
              setActivePage(
                "dashboard"
              )
            }
          >
            <Home size={18} />
            <span>Dashboard</span>
          </button>


          <button
            className={
              activePage === "automation"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActivePage(
                "automation"
              )
            }
          >
            <Play size={18} />
            <span>Automation</span>
          </button>


          <button
            className={
              activePage === "results"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActivePage(
                "results"
              )
            }
          >
            <TrendingUp size={18} />
            <span>Results</span>
          </button>

        </div>


        <div className="sidebar-section">

          <p className="sidebar-label">
            SYSTEM
          </p>


          <button
            className="nav-item"
            onClick={() =>
              setActivePage(
                "settings"
              )
            }
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

        </div>


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
                {backendStatus ===
                "online"
                  ? "Connected"
                  : backendStatus ===
                      "checking"
                    ? "Checking..."
                    : "Offline"}
              </span>

            </div>

          </div>

        </div>

      </aside>


      {/* ====================================================
          MAIN
      ==================================================== */}

      <main className="main-content">

        {/* TOPBAR */}

        <header className="topbar">

          <div>

            <p className="eyebrow">
              BSP INVENTORY AUTOMATION
            </p>

            <h1>
              {activePage ===
              "dashboard"
                ? "Inventory Dashboard"
                : activePage ===
                    "automation"
                  ? "Run Automation"
                  : activePage ===
                      "results"
                    ? "Inventory Results"
                    : "System Settings"}
            </h1>

          </div>


          <div className="topbar-actions">

            <button
              className="icon-button"
              onClick={
                checkBackend
              }
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


        {/* NOTIFICATION */}

        {notification && (

          <div className="notification success">

            <CheckCircle2
              size={18}
            />

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


        {/* ERROR */}

        {error && (

          <div className="notification error">

            <CircleAlert
              size={18}
            />

            <div>

              <strong>
                Automation Error
              </strong>

              <span>
                {error}
              </span>

            </div>

            <button
              onClick={() =>
                setError("")
              }
            >
              <XCircle size={17} />
            </button>

          </div>

        )}


        {/* ==================================================
            DASHBOARD
        ================================================== */}

        {activePage ===
          "dashboard" && (

          <section className="page">

            <div className="hero-card">

              <div className="hero-content">

                <div className="hero-badge">
                  <Activity
                    size={15}
                  />
                  Deterministic Automation
                </div>

                <h2>
                  Automate your BSP
                  inventory workflow.
                </h2>

                <p>
                  Upload the raw Previous
                  and Current MC.1 Excel
                  workbooks and let the
                  backend execute the
                  complete inventory
                  pipeline.
                </p>

                <button
                  className="primary-button"
                  onClick={() =>
                    setActivePage(
                      "automation"
                    )
                  }
                  disabled={
                    running
                  }
                >
                  <Play size={18} />
                  Run Inventory Automation
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
                  MC.1
                </div>

                <div className="visual-line" />

                <div className="visual-node">
                  Report
                </div>

              </div>

            </div>


            <div className="stats-grid">

              <StatCard
                title="New Materials"
                value={
                  newMaterials
                }
                icon={
                  <Upload
                    size={20}
                  />
                }
              />

              <StatCard
                title="Removed Materials"
                value={
                  removedMaterials
                }
                icon={
                  <XCircle
                    size={20}
                  />
                }
              />

              <StatCard
                title="Existing Materials"
                value={
                  existingMaterials
                }
                icon={
                  <RefreshCw
                    size={20}
                  />
                }
              />

              <StatCard
                title="Quantity Change"
                value={
                  formatNumber(
                    quantityChange
                  )
                }
                icon={
                  <TrendingUp
                    size={20}
                  />
                }
              />

            </div>


            <div className="content-grid">

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


                <HealthRow
                  title="FastAPI Backend"
                  description={
                    backendStatus ===
                    "online"
                      ? "API is responding normally"
                      : backendStatus ===
                          "checking"
                        ? "Checking API connection..."
                        : "Backend connection unavailable"
                  }
                  status={
                    backendStatus ===
                    "online"
                      ? "Online"
                      : backendStatus ===
                          "checking"
                        ? "Checking"
                        : "Offline"
                  }
                  icon={
                    <Activity
                      size={19}
                    />
                  }
                />


                <HealthRow
                  title="Inventory Engine"
                  description="Excel processing pipeline"
                  status="Ready"
                  icon={
                    <FileSpreadsheet
                      size={19}
                    />
                  }
                />


                <HealthRow
                  title="Report Validation"
                  description="Generated reports are validated"
                  status="Ready"
                  icon={
                    <ShieldCheck
                      size={19}
                    />
                  }
                />

              </div>

            </div>

          </section>
        )}


        {/* ==================================================
            AUTOMATION
        ================================================== */}

        {activePage ===
          "automation" && (

          <section className="page">

            <div className="page-intro">

              <p className="panel-kicker">
                INVENTORY WORKFLOW
              </p>

              <h2>
                Run BSP Inventory Automation
              </h2>

              <p>
                Upload the two raw MC.1
                Excel workbooks. The
                backend will process,
                compare and generate
                the inventory output.
              </p>

            </div>


            <div className="automation-card automation-config-card">

              <div className="automation-card-header">

                <div className="automation-icon">
                  <FileSpreadsheet
                    size={35}
                  />
                </div>

                <div>

                  <p className="panel-kicker">
                    INPUT DATA
                  </p>

                  <h3>
                    MC.1 Raw Inventory
                  </h3>

                  <p className="automation-muted">
                    Upload Sheet 1 raw
                    Excel files exactly as
                    exported from your
                    inventory process.
                  </p>

                </div>

              </div>


              {/* FILE UPLOAD */}

              <div className="inventory-upload-section">

                <div className="inventory-upload-header">

                  <div>

                    <p className="panel-kicker">
                      RAW INPUT FILES
                    </p>

                    <h4>
                      Previous & Current
                    </h4>

                    <p>
                      The files can contain
                      the raw Sheet 1 data.
                      You do not need to
                      manually clean them
                      before uploading.
                    </p>

                  </div>

                  <span className="upload-required">
                    2 files required
                  </span>

                </div>


                <div className="inventory-upload-grid">

                  <FileUploadBox
                    label="Previous Inventory"
                    description="Previous month / period raw MC.1 data"
                    file={previousFile}
                    disabled={
                      running
                    }
                    onChange={
                      setPreviousFile
                    }
                  />


                  <FileUploadBox
                    label="Current Inventory"
                    description="Current month / period raw MC.1 data"
                    file={currentFile}
                    disabled={
                      running
                    }
                    onChange={
                      setCurrentFile
                    }
                  />

                </div>


                <div className="upload-status-row">

                  <span
                    className={
                      previousFile
                        ? "file-ready"
                        : "file-missing"
                    }
                  >
                    {previousFile
                      ? "✓ Previous raw file ready"
                      : "○ Previous raw file required"}
                  </span>


                  <span
                    className={
                      currentFile
                        ? "file-ready"
                        : "file-missing"
                    }
                  >
                    {currentFile
                      ? "✓ Current raw file ready"
                      : "○ Current raw file required"}
                  </span>

                </div>

              </div>


              {/* CONFIGURATION */}

              <div className="automation-config-grid">

                <label className="automation-field">

                  <span>
                    Previous Period
                  </span>

                  <select
                    value={
                      previousPeriod
                    }
                    onChange={(event) =>
                      setPreviousPeriod(
                        event.target.value
                      )
                    }
                    disabled={
                      running
                    }
                  >

                    <option>
                      Previous Month
                    </option>

                    <option>
                      Previous Quarter
                    </option>

                    <option>
                      Previous Year
                    </option>

                  </select>

                </label>


                <label className="automation-field">

                  <span>
                    Current Period
                  </span>

                  <select
                    value={
                      currentPeriod
                    }
                    onChange={(event) =>
                      setCurrentPeriod(
                        event.target.value
                      )
                    }
                    disabled={
                      running
                    }
                  >

                    <option>
                      Current Month
                    </option>

                    <option>
                      Current Quarter
                    </option>

                    <option>
                      Current Year
                    </option>

                  </select>

                </label>


                <label className="automation-field">

                  <span>
                    Plant
                  </span>

                  <input
                    type="text"
                    value={
                      selectedPlant
                    }
                    onChange={(event) =>
                      setSelectedPlant(
                        event.target.value
                      )
                    }
                    placeholder="1000"
                    disabled={
                      running
                    }
                  />

                </label>


                <label className="automation-field">

                  <span>
                    Storage Location
                  </span>

                  <select
                    value={
                      storageLocation
                    }
                    onChange={(event) =>
                      setStorageLocation(
                        event.target.value
                      )
                    }
                    disabled={
                      running
                    }
                  >

                    <option>
                      All
                    </option>

                    <option>
                      Configured
                    </option>

                  </select>

                </label>

              </div>


              {/* FIXED SAP CONFIG */}

              <div className="automation-fixed-config">

                <div>
                  <span>
                    SAP Transaction
                  </span>

                  <strong>
                    MC.1
                  </strong>
                </div>


                <div>
                  <span>
                    Variant
                  </span>

                  <strong>
                    B002159
                  </strong>
                </div>


                <div>
                  <span>
                    Execution Mode
                  </span>

                  <strong>
                    Offline / Raw Excel
                  </strong>
                </div>

              </div>


              {/* PROGRESS */}

              {running && (

                <div className="run-progress">

                  <div className="run-progress-header">

                    <span>
                      Processing inventory...
                    </span>

                    <strong>
                      {uploadProgress}%
                    </strong>

                  </div>

                  <div className="progress-track">

                    <div
                      className="progress-fill"
                      style={{
                        width:
                          `${uploadProgress}%`,
                      }}
                    />

                  </div>

                  {runId && (
                    <small>
                      Run ID: {runId}
                    </small>
                  )}

                </div>

              )}


              {/* RUN BUTTON */}

              <button
                className="primary-button large automation-run-button"
                onClick={
                  runAutomation
                }
                disabled={
                  running ||
                  !previousFile ||
                  !currentFile
                }
              >

                {running ? (

                  <>
                    <Loader2
                      size={20}
                      className="spin"
                    />

                    Processing Inventory...
                  </>

                ) : (

                  <>
                    <Play
                      size={20}
                    />

                    Run BSP Automation
                  </>

                )}

              </button>


              {/* RESET */}

              {!running &&
                (previousFile ||
                  currentFile ||
                  workflowResult) && (

                <button
                  className="secondary-button"
                  onClick={
                    resetRun
                  }
                >
                  Reset Current Run
                </button>

              )}

            </div>


            {/* LIVE WORKFLOW */}

            <div className="workflow-preview">

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <p className="panel-kicker">
                      LIVE EXECUTION
                    </p>

                    <h3>
                      Automation Pipeline
                    </h3>

                  </div>

                  <Activity
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

            </div>

          </section>
        )}


        {/* ==================================================
            RESULTS
        ================================================== */}

        {activePage ===
          "results" && (

          <section className="page">

            <div className="page-intro">

              <p className="panel-kicker">
                AUTOMATION OUTPUT
              </p>

              <h2>
                Inventory Results
              </h2>

              <p>
                Results generated by
                the latest BSP automation
                run.
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
                  Upload Previous and
                  Current raw MC.1 files
                  and run the automation.
                </p>

                <button
                  className="primary-button"
                  onClick={() =>
                    setActivePage(
                      "automation"
                    )
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
                    value={
                      newMaterials
                    }
                    icon={
                      <Upload
                        size={20}
                      />
                    }
                  />

                  <StatCard
                    title="Removed Materials"
                    value={
                      removedMaterials
                    }
                    icon={
                      <XCircle
                        size={20}
                      />
                    }
                  />

                  <StatCard
                    title="Existing Materials"
                    value={
                      existingMaterials
                    }
                    icon={
                      <RefreshCw
                        size={20}
                      />
                    }
                  />

                  <StatCard
                    title="Quantity Change"
                    value={
                      formatNumber(
                        quantityChange
                      )
                    }
                    icon={
                      <TrendingUp
                        size={20}
                      />
                    }
                  />

                </div>


                {/* AI ANALYSIS */}

                {inventoryAnalysis && (

                  <div className="results-panel">

                    <div className="panel-header">

                      <div>

                        <p className="panel-kicker">
                          AI INVENTORY ANALYSIS
                        </p>

                        <h3>
                          Inventory Intelligence
                        </h3>

                      </div>

                      <div
                        className={`analysis-risk ${String(
                          analysisRisk
                        ).toLowerCase()}`}
                      >
                        {analysisRisk}
                      </div>

                    </div>


                    <div className="analysis-stats">

                      <div className="analysis-stat">
                        <span>
                          Significant Changes
                        </span>

                        <strong>
                          {
                            significantChanges.length
                          }
                        </strong>
                      </div>


                      <div className="analysis-stat">
                        <span>
                          Zero Stock Materials
                        </span>

                        <strong>
                          {
                            formatNumber(
                              zeroStockMaterials
                            )
                          }
                        </strong>
                      </div>


                      <div className="analysis-stat">
                        <span>
                          Top Increases
                        </span>

                        <strong>
                          {
                            topIncreases.length
                          }
                        </strong>
                      </div>


                      <div className="analysis-stat">
                        <span>
                          Top Decreases
                        </span>

                        <strong>
                          {
                            topDecreases.length
                          }
                        </strong>
                      </div>

                    </div>


                    {recommendations.length >
                      0 && (

                      <div className="analysis-section">

                        <div className="analysis-section-title">

                          <ShieldCheck
                            size={17}
                          />

                          <strong>
                            Recommendations
                          </strong>

                        </div>


                        <div className="recommendation-list">

                          {recommendations
                            .slice(0, 5)
                            .map(
                              (
                                recommendation,
                                index
                              ) => (

                                <div
                                  className="recommendation-item"
                                  key={
                                    index
                                  }
                                >

                                  <span className="recommendation-number">
                                    {
                                      index +
                                      1
                                    }
                                  </span>

                                  <span>
                                    {typeof recommendation ===
                                    "string"
                                      ? recommendation
                                      : recommendation?.message ||
                                        recommendation?.recommendation ||
                                        JSON.stringify(
                                          recommendation
                                        )}
                                  </span>

                                </div>

                              )
                            )}

                        </div>

                      </div>

                    )}

                  </div>

                )}


                {/* CLASSIFICATION */}

                {classificationResult && (

                  <div className="results-panel">

                    <div className="panel-header">

                      <div>

                        <p className="panel-kicker">
                          MATERIAL CLASSIFICATION
                        </p>

                        <h3>
                          RI / Capital Classification
                        </h3>

                      </div>

                      <ShieldCheck
                        size={28}
                      />

                    </div>


                    <div className="stats-grid">

                      <StatCard
                        title="RI Materials"
                        value={
                          classificationCounts.ri
                        }
                        icon={
                          <ShieldCheck
                            size={20}
                          />
                        }
                      />


                      <StatCard
                        title="Capital Materials"
                        value={
                          classificationCounts.capital
                        }
                        icon={
                          <BarChart3
                            size={20}
                          />
                        }
                      />


                      <StatCard
                        title="Normal Materials"
                        value={
                          classificationCounts.normal
                        }
                        icon={
                          <CheckCircle2
                            size={20}
                          />
                        }
                      />


                      <StatCard
                        title="Unclassified"
                        value={
                          classificationCounts.unclassified
                        }
                        icon={
                          <CircleAlert
                            size={20}
                          />
                        }
                      />

                    </div>


                    {classificationRows.length >
                      0 && (

                      <div className="table-wrapper">

                        <table className="inventory-table">

                          <thead>

                            <tr>
                              <th>
                                Material
                              </th>

                              <th>
                                Material Name
                              </th>

                              <th>
                                Inventory Type
                              </th>

                              <th>
                                Reason
                              </th>
                            </tr>

                          </thead>


                          <tbody>

                            {classificationRows.map(
                              (row) => {

                                const type =
                                  String(
                                    row.inventoryType
                                  ).toUpperCase();


                                const typeClass =
                                  type === "RI"
                                    ? "ri"
                                    : type ===
                                        "CAPITAL"
                                      ? "capital"
                                      : type ===
                                          "NORMAL"
                                        ? "normal"
                                        : "unclassified";


                                return (

                                  <tr
                                    key={
                                      row.id
                                    }
                                  >

                                    <td>
                                      <strong className="material-code">
                                        {
                                          row.materialCode
                                        }
                                      </strong>
                                    </td>

                                    <td>
                                      {
                                        row.materialName
                                      }
                                    </td>

                                    <td>
                                      <span
                                        className={`status-badge classification-badge ${typeClass}`}
                                      >
                                        {type}
                                      </span>
                                    </td>

                                    <td>
                                      {
                                        row.classificationReason
                                      }
                                    </td>

                                  </tr>

                                );
                              }
                            )}

                          </tbody>

                        </table>

                      </div>

                    )}

                  </div>

                )}


                {/* COMPARISON TABLE */}

                <div className="results-table-panel">

                  <div className="results-table-header">

                    <div>

                      <p className="panel-kicker">
                        MATERIAL ANALYSIS
                      </p>

                      <h3>
                        Inventory Changes
                      </h3>

                      <span className="results-count">
                        Showing{" "}
                        {
                          displayedRows.length
                        }{" "}
                        of{" "}
                        {
                          normalizedRows.length
                        }{" "}
                        materials
                      </span>

                    </div>


                    <div className="table-controls">

                      <div className="search-box">

                        <Search
                          size={17}
                        />

                        <input
                          type="text"
                          placeholder="Search material, name or plant..."
                          value={
                            resultSearch
                          }
                          onChange={(event) =>
                            setResultSearch(
                              event.target.value
                            )
                          }
                        />

                      </div>


                      <div className="filter-box">

                        <Filter
                          size={16}
                        />

                        <select
                          value={
                            resultFilter
                          }
                          onChange={(event) =>
                            setResultFilter(
                              event.target.value
                            )
                          }
                        >

                          <option value="All">
                            All Status
                          </option>

                          <option value="New">
                            New
                          </option>

                          <option value="Existing">
                            Existing
                          </option>

                          <option value="Removed">
                            Removed
                          </option>

                        </select>

                      </div>


                      <div className="filter-box">

                        <ArrowUpDown
                          size={16}
                        />

                        <select
                          value={
                            resultSort
                          }
                          onChange={(event) =>
                            setResultSort(
                              event.target.value
                            )
                          }
                        >

                          <option value="none">
                            Default Order
                          </option>

                          <option value="material">
                            Material Code
                          </option>

                          <option value="quantity-desc">
                            Quantity Change ↓
                          </option>

                          <option value="quantity-asc">
                            Quantity Change ↑
                          </option>

                        </select>

                      </div>

                    </div>

                  </div>


                  {displayedRows.length ===
                  0 ? (

                    <div className="table-empty">

                      <Search
                        size={32}
                      />

                      <h4>
                        No materials found
                      </h4>

                      <p>
                        Try changing your
                        search or filter.
                      </p>

                    </div>

                  ) : (

                    <div className="table-wrapper">

                      <table className="inventory-table">

                        <thead>

                          <tr>
                            <th>
                              Material
                            </th>

                            <th>
                              Material Name
                            </th>

                            <th>
                              Previous Qty
                            </th>

                            <th>
                              Current Qty
                            </th>

                            <th>
                              Change
                            </th>

                            <th>
                              Unit
                            </th>

                            <th>
                              Plant
                            </th>

                            <th>
                              Status
                            </th>
                          </tr>

                        </thead>


                        <tbody>

                          {displayedRows.map(
                            (row) => {

                              const change =
                                row.quantityChange;


                              const status =
                                String(
                                  row.status
                                ).toLowerCase();


                              return (

                                <tr
                                  key={
                                    row.id
                                  }
                                >

                                  <td>
                                    <strong className="material-code">
                                      {
                                        row.materialCode
                                      }
                                    </strong>
                                  </td>


                                  <td>
                                    <span className="material-name">
                                      {
                                        row.materialName
                                      }
                                    </span>
                                  </td>


                                  <td>
                                    {
                                      formatNumber(
                                        row.previousQuantity
                                      )
                                    }
                                  </td>


                                  <td>
                                    {
                                      formatNumber(
                                        row.currentQuantity
                                      )
                                    }
                                  </td>


                                  <td>

                                    <span
                                      className={
                                        change >
                                        0
                                          ? "quantity-change positive"
                                          : change <
                                              0
                                            ? "quantity-change negative"
                                            : "quantity-change neutral"
                                      }
                                    >
                                      {change >
                                      0
                                        ? "+"
                                        : ""}
                                      {
                                        formatNumber(
                                          change
                                        )
                                      }
                                    </span>

                                  </td>


                                  <td>
                                    {
                                      row.unit
                                    }
                                  </td>


                                  <td>
                                    {
                                      row.plant
                                    }
                                  </td>


                                  <td>

                                    <span
                                      className={`status-badge ${status}`}
                                    >
                                      {
                                        row.status
                                      }
                                    </span>

                                  </td>

                                </tr>

                              );
                            }
                          )}

                        </tbody>

                      </table>

                    </div>

                  )}

                </div>


                {/* FINAL STATUS */}

                <div className="results-panel">

                  <div className="panel-header">

                    <div>

                      <p className="panel-kicker">
                        FINAL STATUS
                      </p>

                      <h3>
                        {[
                          "completed",
                          "complete",
                          "success",
                        ].includes(
                          workflowStatus
                        )
                          ? "Workflow Completed"
                          : "Workflow Result"}
                      </h3>

                    </div>

                    <CheckCircle2
                      size={28}
                    />

                  </div>


                  <div
                    className={
                      [
                        "completed",
                        "complete",
                        "success",
                      ].includes(
                        workflowStatus
                      )
                        ? "result-success"
                        : "result-warning"
                    }
                  >

                    {[
                      "completed",
                      "complete",
                      "success",
                    ].includes(
                      workflowStatus
                    ) ? (
                      <CheckCircle2
                        size={24}
                      />
                    ) : (
                      <CircleAlert
                        size={24}
                      />
                    )}


                    <div>

                      <strong>
                        {[
                          "completed",
                          "complete",
                          "success",
                        ].includes(
                          workflowStatus
                        )
                          ? "Inventory report generated successfully."
                          : "Inventory workflow has not completed successfully."}
                      </strong>

                      <span>
                        {runId
                          ? `Run ID: ${runId}`
                          : "No run ID available."}
                      </span>

                    </div>

                  </div>


                  <div className="download-actions">

                    <button
                      className="primary-button"
                      onClick={() =>
                        downloadBspFile(
                          "BSP_Inventory.xlsx"
                        )
                      }
                      disabled={
                        !runId
                      }
                    >

                      <Download
                        size={19}
                      />

                      Download BSP Inventory

                    </button>


                    <button
                      className="secondary-button"
                      onClick={() =>
                        downloadBspFile(
                          "Inventory PO.xlsx"
                        )
                      }
                      disabled={
                        !runId
                      }
                    >

                      <Download
                        size={19}
                      />

                      Download Inventory PO

                    </button>

                  </div>

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


        {/* ==================================================
            SETTINGS
        ================================================== */}

        {activePage ===
          "settings" && (

          <section className="page">

            <div className="page-intro">

              <p className="panel-kicker">
                CONFIGURATION
              </p>

              <h2>
                System Settings
              </h2>

              <p>
                Current BSP inventory
                automation configuration.
              </p>

            </div>


            <div className="settings-grid">

              <Setting
                label="API Server"
                value={
                  API_BASE_URL
                }
              />

              <Setting
                label="BSP Endpoint"
                value="/bsp/run"
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
                value={
                  selectedPlant
                }
              />

              <Setting
                label="Execution Mode"
                value="Offline / Raw Excel"
              />

            </div>

          </section>

        )}

      </main>

    </div>
  );
}


// ============================================================
// FILE UPLOAD BOX
// ============================================================

function FileUploadBox({
  label,
  description,
  file,
  disabled,
  onChange,
}) {

  return (

    <label
      className={
        `inventory-file-box ${
          file
            ? "has-file"
            : ""
        }`
      }
    >

      <div className="inventory-file-icon">

        <FileSpreadsheet
          size={25}
        />

      </div>


      <div className="inventory-file-content">

        <strong>
          {label}
        </strong>

        <span>
          {description}
        </span>


        {file ? (

          <small
            title={
              file.name
            }
          >
            {file.name}
          </small>

        ) : (

          <small>
            No file selected
          </small>

        )}

      </div>


      <span className="choose-file-button">

        {file
          ? "Change File"
          : "Choose File"}

      </span>


      <input
        type="file"
        accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
        onChange={(
          event
        ) =>
          onChange(
            event.target.files?.[0] ||
            null
          )
        }
        disabled={
          disabled
        }
      />

    </label>
  );
}


// ============================================================
// STAT CARD
// ============================================================

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


// ============================================================
// HEALTH ROW
// ============================================================

function HealthRow({
  title,
  description,
  status,
  icon,
}) {

  const statusClass =
    status === "Online" ||
    status === "Ready"
      ? "good"
      : status ===
          "Checking"
        ? ""
        : "bad";


  return (

    <div className="health-row">

      <div className="health-icon">
        {icon}
      </div>

      <div>

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>

      <div
        className={`health-status ${statusClass}`}
      >
        {status}
      </div>

    </div>
  );
}


// ============================================================
// WORKFLOW LIST
// ============================================================

function WorkflowList({
  workflowResult,
  getStepStatus,
}) {

  return (

    <div className="workflow-list">

      {WORKFLOW_STEPS.map(
        (
          stepName,
          index
        ) => {

          const status =
            workflowResult
              ? getStepStatus(
                  stepName
                )
              : "pending";


          return (

            <div
              className="workflow-item"
              key={
                stepName
              }
            >

              <div className="workflow-number">

                {status ===
                "completed" ? (

                  <CheckCircle2
                    size={21}
                  />

                ) : status ===
                  "failed" ? (

                  <XCircle
                    size={21}
                  />

                ) : status ===
                  "running" ? (

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

                  {status ===
                  "completed"
                    ? "Completed successfully"
                    : status ===
                        "running"
                      ? "Currently running"
                      : status ===
                          "failed"
                        ? "Step failed"
                        : "Waiting"}

                </span>

              </div>


              <div
                className={`workflow-status ${status}`}
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


// ============================================================
// SETTING
// ============================================================

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


// ============================================================
// EXPORT
// ============================================================

export default App;