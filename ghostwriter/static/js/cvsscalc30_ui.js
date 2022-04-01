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
    var output  = CVSS.calculateCVSSFromMetrics(AttackVector(),AttackComplexity(),PrivilegesRequired(),UserInteraction(),Scope(),Confidentiality(),Integrity(),Availability());
    var result;
      if (output.success === true) {
    result =
      "Base score is " + output.baseMetricScore + ". " +
      "Base severity is " + output.baseSeverity + ". " +
      "Vector string is " + output.vectorString + ". ";
      document.getElementById('id_cvss_score').value = output.baseMetricScore;
      document.getElementById('id_cvss_vector').value = output.vectorString;

      if (output.baseMetricScore >= 9.0){
          document.getElementById('id_severity').value = 5;
      }
      else if(output.baseMetricScore >= 7.0){
        document.getElementById('id_severity').value = 4;
      }
      else if(output.baseMetricScore >= 4.0){
        document.getElementById('id_severity').value = 3;
      }
      else if(output.baseMetricScore >= 0.1){
        document.getElementById('id_severity').value = 2;
      }
      else{
        document.getElementById('id_severity').value = 1;
      }
      document.getElementById("scoreRating").className = "scoreRating " + output.baseSeverity.toLowerCase();
      document.getElementById("baseMetricScore").textContent = output.baseMetricScore;
      document.getElementById("baseSeverity").textContent = "("+output.baseSeverity+")";


  } else {
    result =
      "An error occurred. The error type is '" + errorType +
      "' and the metrics with errors are " + errorMetrics + ".";
  }
}