function cvsscalc40_ui() {
    var iframe = document.getElementById('cvsscalc40');
    var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    iframeDoc.onclick = function() {
        // Get the CVSS score from the iframe
        var text = iframeDoc.querySelector('h5.score-line').innerText;
        var cvss_score = text.split(':')[1].split('/')[0].trim();

        // Get the CVSS vector from the iframe
        var urlFragment = iframe.contentWindow.location.hash;
        var cvss_vector = urlFragment.split('#')[1];

        // Set input fields in ghostwriter
        document.getElementById('id_cvss_score').value = cvss_score;
        document.getElementById('id_cvss_vector').value = cvss_vector;

        if (cvss_score >= 9.0){
            document.getElementById('id_severity').value = 5;
        }
        else if(cvss_score >= 7.0){
          document.getElementById('id_severity').value = 4;
        }
        else if(cvss_score >= 4.0){
          document.getElementById('id_severity').value = 3;
        }
        else if(cvss_score >= 0.1){
          document.getElementById('id_severity').value = 2;
        }
        else{
          document.getElementById('id_severity').value = 1;
        }
    }
}

function ParseVectorCVSS4(vectorString){
    var iframe = document.getElementById('cvsscalc40');
    var currentSrc = iframe.src;
    iframe.src = currentSrc.split('#')[0] + '#' + vectorString;
}