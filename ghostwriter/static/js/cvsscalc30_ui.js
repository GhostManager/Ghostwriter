function AttackVector(){
  if (AV_N.checked) {return "N";}
  else if (AV_A.checked) {return "A";}
  else if (AV_L.checked) {return "L";}
  else if (AV_P.checked) {return "P";}
  else {return null;}
}

function AttackComplexity(){
  if (AC_L.checked) {return "L";}
  else if (AC_H.checked) {return "H";}
  else {return null;}
}

function PrivilegesRequired(){
  if (PR_N.checked) {return "N";}
  else if (PR_L.checked) {return "L";}
  else if (PR_H.checked) {return "H";}
  else {return null;}
}

function UserInteraction(){
  if (UI_N.checked) {return "N";}
  else if (UI_R.checked) {return "R";}
  else {return null;}
}

function Scope(){
  if (S_U.checked) {return "U";}
  else if (S_C.checked) {return "C";}
  else {return null;}
}

function Confidentiality(){
  if (C_N.checked) {return "N";}
  else if (C_L.checked) {return "L";}
  else if (C_H.checked) {return "H";}
  else {return null;}
}

function Integrity (){
  if (I_N.checked) {return "N";}
  else if (I_L.checked) {return "L";}
  else if (I_H.checked) {return "H";}
  else {return null;}
}

function Availability(){
  if (A_N.checked) {return "N";}
  else if (A_L.checked) {return "L";}
  else if (A_H.checked) {return "H";}
  else {return null;}
}

function ModifiedAttackVector(){
  if (MAV_X.checked) {return "X";}
  else if (MAV_N.checked) {return "N";}
  else if (MAV_A.checked) {return "A";}
  else if (MAV_L.checked) {return "L";}
  else if (MAV_P.checked) {return "P";}
  else {return null;}
}

function ModifiedAttackComplexity(){
  if (MAC_X.checked) {return "X";}
  else if (MAC_L.checked) {return "L";}
  else if (MAC_H.checked) {return "H";}
  else {return null;}
}

function ModifiedPrivilegesRequired(){
  if (MPR_X.checked) {return "X";}
  else if (MPR_N.checked) {return "N";}
  else if (MPR_L.checked) {return "L";}
  else if (MPR_H.checked) {return "H";}
  else {return null;}
}

function ModifiedUserInteraction(){
  if (MUI_X.checked) {return "X";}
  else if (MUI_N.checked) {return "N";}
  else if (MUI_R.checked) {return "R";}
  else {return null;}
}

function ModifiedScope(){
  if (MS_X.checked) {return "X";}
  else if (MS_U.checked) {return "U";}
  else if (MS_C.checked) {return "C";}
  else {return null;}
}

function ModifiedConfidentiality(){
  if (MC_X.checked) {return "X";}
  else if (MC_N.checked) {return "N";}
  else if (MC_L.checked) {return "L";}
  else if (MC_H.checked) {return "H";}
  else {return null;}
}

function ModifiedIntegrity (){
  if (MI_X.checked) {return "X";}
  else if (MI_N.checked) {return "N";}
  else if (MI_L.checked) {return "L";}
  else if (MI_H.checked) {return "H";}
  else {return null;}
}

function ModifiedAvailability(){
  if (MA_X.checked) {return "X";}
  else if (MA_N.checked) {return "N";}
  else if (MA_L.checked) {return "L";}
  else if (MA_H.checked) {return "H";}
  else {return null;}
}

function ConfidentialityRequirement(){
  if (CR_X.checked) {return "X";}
  else if (CR_L.checked) {return "L";}
  else if (CR_M.checked) {return "M";}
  else if (CR_H.checked) {return "H";}
  else {return null;}
}

function IntegrityRequirement(){
  if (IR_X.checked) {return "X";}
  else if (IR_L.checked) {return "L";}
  else if (IR_M.checked) {return "M";}
  else if (IR_H.checked) {return "H";}
  else {return null;}
}

function AvailabilityRequirement(){
  if (IR_X.checked) {return "X";}
  else if (IR_L.checked) {return "L";}
  else if (IR_M.checked) {return "M";}
  else if (IR_H.checked) {return "H";}
  else {return null;}
}

// JS function to check cvss fields on page load
function ParseVector(vectorString){
  var metricValues = {
    AV:  undefined, AC:  undefined, PR:  undefined, UI:  undefined, S:  undefined,
    C:   undefined, I:   undefined, A:   undefined,
    E:   undefined, RL:  undefined, RC:  undefined,
    CR:  undefined, IR:  undefined, AR:  undefined,
    MAV: undefined, MAC: undefined, MPR: undefined, MUI: undefined, MS: undefined,
    MC:  undefined, MI:  undefined, MA:  undefined
  };
  var metricNameValue = vectorString.substring(CVSS.CVSSVersionIdentifier.length).split("/");
  for (var i in metricNameValue) {
    if (metricNameValue.hasOwnProperty(i)) {

      var singleMetric = metricNameValue[i].split(":");

      if (typeof metricValues[singleMetric[0]] === "undefined") {
        metricValues[singleMetric[0]] = singleMetric[1];
      }
    }
  }
  switch (metricValues.AV) {
    case 'N':
      AV_N.checked = true;
      break;
    case 'A':
      AV_A.checked = true;
      break;
    case 'L':
      AV_L.checked = true;
      break;
    case 'P':
      AV_P.checked = true;
      break;
    }
  switch (metricValues.AC) {
    case 'L':
      AC_L.checked = true;
      break;
    case 'H':
      AC_H.checked = true;
      break;
    }
  switch (metricValues.PR) {
    case 'N':
      PR_N.checked = true;
      break;
    case 'L':
      PR_L.checked = true;
      break;
    case 'H':
      PR_H.checked = true;
      break;
    }
  switch (metricValues.UI) {
    case 'R':
      UI_R.checked = true;
      break;
    case 'N':
      UI_N.checked = true;
      break;
    }
  switch (metricValues.S) {
    case 'U':
      S_U.checked = true;
      break;
    case 'C':
      S_C.checked = true;
      break;
    }
  switch (metricValues.C) {
    case 'N':
      C_N.checked = true;
      break;
    case 'L':
      C_L.checked = true;
      break;
    case 'H':
      C_H.checked = true;
      break;
    }
  switch (metricValues.I) {
    case 'N':
      I_N.checked = true;
      break;
    case 'L':
      I_L.checked = true;
      break;
    case 'H':
      I_H.checked = true;
      break;
    }
  switch (metricValues.A) {
    case 'N':
      A_N.checked = true;
      break;
    case 'L':
      A_L.checked = true;
      break;
    case 'H':
      A_H.checked = true;
      break;
    }
  switch (metricValues.MAV) {
    case 'N':
      MAV_N.checked = true;
      break;
    case 'A':
      MAV_A.checked = true;
      break;
    case 'L':
      MAV_L.checked = true;
      break;
    case 'P':
      MAV_P.checked = true;
      break;
    case 'X':
    default:
        MAV_X.checked = true;
        break;
    }
  switch (metricValues.MAC) {
    case 'L':
      MAC_L.checked = true;
      break;
    case 'H':
      MAC_H.checked = true;
      break;
    case 'X':
    default:
        MAC_X.checked = true;
        break;
    }
  switch (metricValues.MPR) {
    case 'N':
      MPR_N.checked = true;
      break;
    case 'L':
      MPR_L.checked = true;
      break;
    case 'H':
      MPR_H.checked = true;
      break;
    case 'X':
    default:
        MPR_X.checked = true;
        break;
    }
  switch (metricValues.MUI) {
    case 'R':
      MUI_R.checked = true;
      break;
    case 'N':
      MUI_N.checked = true;
      break;
    case 'X':
    default:
        MUI_X.checked = true;
        break;
    }
  switch (metricValues.MS) {
    case 'U':
      MS_U.checked = true;
      break;
    case 'C':
      MS_C.checked = true;
      break;
    case 'X':
    default:
        MS_X.checked = true;
        break;
    }
  switch (metricValues.MC) {
    case 'N':
      MC_N.checked = true;
      break;
    case 'L':
      MC_L.checked = true;
      break;
    case 'H':
      MC_H.checked = true;
      break;
    case 'X':
    default:
        MC_X.checked = true;
        break;
    }
  switch (metricValues.MI) {
    case 'N':
      MI_N.checked = true;
      break;
    case 'L':
      MI_L.checked = true;
      break;
    case 'H':
      MI_H.checked = true;
      break;
    case 'X':
    default:
        MI_X.checked = true;
        break;
    }
  switch (metricValues.MA) {
    case 'N':
      MA_N.checked = true;
      break;
    case 'L':
      MA_L.checked = true;
      break;
    case 'H':
      MA_H.checked = true;
      break;
    case 'X':
    default:
        MA_X.checked = true;
        break;
    }
  switch (metricValues.CR) {
    case 'L':
      CR_L.checked = true;
      break;
    case 'M':
      CR_M.checked = true;
      break;
    case 'H':
      CR_H.checked = true;
      break;
    case 'X':
    default:
        CR_X.checked = true;
        break;
    }
  switch (metricValues.IR) {
    case 'L':
      IR_L.checked = true;
      break;
    case 'M':
      IR_M.checked = true;
      break;
    case 'H':
      IR_H.checked = true;
      break;
    case 'X':
    default:
        IR_X.checked = true;
        break;
    }
  switch (metricValues.AR) {
    case 'L':
      AR_L.checked = true;
      break;
    case 'M':
      AR_M.checked = true;
      break;
    case 'H':
      AR_H.checked = true;
      break;
    case 'X':
    default:
        AR_X.checked = true;
        break;
  }
}
function CVSSAutoCalc(){
  var count = 0
  var fields = ["AV","AC","PR","UI","S","C","I","A"];
  for (i=0; i < fields.length;i++){
    for (j=0; j < document.getElementsByName(fields[i]).length;j++){
      if (document.getElementsByName(fields[i])[j].checked === true){count++}
    }
  }
  if (count == 8){CVSSScore();};
}
function CVSSScore(){
    var output  = CVSS.calculateCVSSFromMetrics(AttackVector(),AttackComplexity(),PrivilegesRequired(),UserInteraction(),Scope(),Confidentiality(),Integrity(),Availability(),
      undefined,undefined,undefined,ConfidentialityRequirement(),IntegrityRequirement(),AvailabilityRequirement(),ModifiedAttackVector(),ModifiedAttackComplexity(),
      ModifiedPrivilegesRequired(),ModifiedUserInteraction(),ModifiedScope(),ModifiedConfidentiality(),ModifiedIntegrity(),ModifiedAvailability());
    var result;
      if (output.success === true) {
    result =
      "Base score is " + output.baseMetricScore + ". " +
      "Base severity is " + output.baseSeverity + ". " +
      "Vector string is " + output.vectorString + ". ";
      var score = output.environmentalMetricScore != undefined ? output.environmentalMetricScore : output.baseMetricScore;
      document.getElementById('id_cvss_score').value = score;
      document.getElementById('id_cvss_vector').value = output.vectorString;

      if (score >= 9.0){
          document.getElementById('id_severity').value = 5;
      }
      else if(score >= 7.0){
        document.getElementById('id_severity').value = 4;
      }
      else if(score >= 4.0){
        document.getElementById('id_severity').value = 3;
      }
      else if(score >= 0.1){
        document.getElementById('id_severity').value = 2;
      }
      else{
        document.getElementById('id_severity').value = 1;
      }
      document.getElementById("scoreRating").className = "scoreRating " + output.baseSeverity.toLowerCase();
      document.getElementById("baseMetricScore").textContent = output.baseMetricScore;
      document.getElementById("baseSeverity").textContent = "("+output.baseSeverity+")";
      document.getElementById("environmentalScoreRating").className = "scoreRating " + output.environmentalSeverity.toLowerCase();
      document.getElementById("environmentalMetricScore").textContent = output.environmentalMetricScore;
      document.getElementById("environmentalSeverity").textContent = "("+output.environmentalSeverity+")";


  } else {
    result =
      "An error occurred. The error type is '" + errorType +
      "' and the metrics with errors are " + errorMetrics + ".";
  }
}