<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
		xmlns="http://www.w3.org/1999/xhtml"
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:xht2="http://www.w3.org/2002/06/xhtml2/"
		xmlns:dct="http://purl.org/dc/terms/"
		xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
		xmlns:rinfo="http://rinfo.lagrummet.se/taxo/2007/09/rinfo/pub#"
		xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
		xmlns:rinfoex="http://lagen.nu/terms#"
		exclude-result-prefixes="xht2">
  <xsl:param name="infile">unknown-infile</xsl:param>
  <xsl:param name="outfile">unknown-outfile</xsl:param>
  <xsl:param name="annotationfile"/>

  <xsl:output method="xml"
  	    doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
  	    doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
	    indent="yes"
	    />

  <!--
      we'd like to use the following doctype, since we're not valid
      w/o it, but IE brings up blank pages when using it (as do FF if
      we're not using application/xhtml+xml) - wonder how eurlex.nu
      does it? -->
  <!--
  <xsl:output method="xml"
	      doctype-public="-//W3C//DTD XHTML+RDFa 1.0//EN"
	      doctype-system="http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd"
	      indent="yes"
	    />
  -->

  <!-- these minimal RDF files is only used to know wheter we have a
       specific case (and therefore should link it) or keyword, so
       that we can know when to link to it -->
  <xsl:variable name="rattsfall" select="document('../data/dv/parsed/rdf-mini.xml')/rdf:RDF"/>
  <xsl:variable name="terms" select="document('../data/keyword/parsed/rdf-mini.xml')/rdf:RDF"/>
  <xsl:variable name="lagkommentar" select="document('../data/sfs/parsed/rdf-mini.xml')/rdf:RDF"/>
  <xsl:variable name="annotations" select="document($annotationfile)/rdf:RDF"/>

  <xsl:template match="/">
    <!--<xsl:message>Root rule</xsl:message>-->
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="xht2:html">
    <!--<xsl:message>base/root</xsl:message>-->
    <html xml:lang="sv"><xsl:apply-templates/></html>
  </xsl:template>
    
  <xsl:template match="xht2:head">
    <!--<xsl:message>base/head</xsl:message>-->
    <head>
      <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
      <title><xsl:call-template name="headtitle"/></title>
      <xsl:call-template name="metarobots"/>
      <script type="text/javascript" src="/js/jquery-1.3.2.min.js"></script>
      <script type="text/javascript" src="/js/jquery-ui-1.7.2.custom.min.js"></script>
      <script type="text/javascript" src="/js/jquery.treeview.min.js"></script>
      <script type="text/javascript" src="/js/base.js"></script>
      <link rel="shortcut icon" href="/img/favicon.ico" type="image/x-icon" />
      <link rel="stylesheet" href="/css/screen.css" media="screen" type="text/css"/> 
      <link rel="stylesheet" href="/css/print.css" media="print" type="text/css"/>
      <link rel="stylesheet" href="/css/jquery-ui-1.7.2.custom.css" type="text/css"/> 
      <xsl:call-template name="linkalternate"/>
      <xsl:call-template name="headmetadata"/>
    </head>
  </xsl:template>

  <xsl:template match="xht2:body">
    <!--<xsl:message>base/body</xsl:message>-->
    <body>
      <xsl:if test="//xht2:html/@about">
	<xsl:attribute name="about"><xsl:value-of select="//xht2:html/@about"/></xsl:attribute>
      </xsl:if>

      <xsl:attribute name="typeof"><xsl:value-of select="@typeof"/></xsl:attribute>

      <xsl:comment>[if lte IE 6]&gt;
	  &lt;style type="text/css"&gt;
	    #ie6msg{border:3px solid #090; margin:8px 0; background:#cfc; color:#000;}
	    #ie6msg h4{margin:8px; padding:0;}
	    #ie6msg p{margin:8px; padding:0; font-size: smaller;}
	    #ie6msg p a.getie7{font-weight:bold; color:#006;}
	    #ie6msg p a.ie6expl{font-weight:normal; color:#006;}
	  &lt;/style&gt;
	  &lt;div id="ie6msg"&gt;
	    &lt;h4&gt;Du har en gammal version av webbläsaren Internet Explorer.&lt;/h4&gt;
	    &lt;p&gt;
	      Det kan hända att sidan på grund av detta ser konstig ut, med överlappande text eller andra problem. 
              För att få en bättre och säkrare upplevelse på nätet
	      rekommenderar vi att du &lt;a class="getie7"
	      href="http://www.microsoft.com/sverige/windows/downloads/ie/getitnow.mspx"&gt;hämtar
	      en nyare version av Internet
	      Explorer&lt;/a&gt;. Uppgraderingen är kostnadsfri.  Sitter du
	      på jobb och inte har kontroll över din dator själv bör
	      du kontakta din IT-ansvarige.
	    &lt;/p&gt;
	    &lt;p&gt;
	      Vi kan också rekommendera dig att prova någon av följade
	      alternativa
	      webbläsare &lt;a href="http://mozilla.com"&gt;Firefox&lt;/a&gt;, 
              &lt;a href="http://www.google.com/chrome"&gt;Chrome&lt;/a&gt;, 
	      &lt;a href="http://www.apple.com/safari/download/"&gt;Safari&lt;/a&gt;
	      eller &lt;a href="http://www.opera.com"&gt;Opera&lt;/a&gt;.
	    &lt;/p&gt;
	    &lt;p&gt;
	      Den här uppmaningen har sitt ursprung i Norge och på en
	      av deras största sajter, finn.no, kan du läsa om
	      &lt;a class="ie6expl"
	      href="http://labs.finn.no/blog/finn-anbefaler-ie6-brukere-a-oppgradere-sin-nettleser"&gt;varför
              du bör uppgradera&lt;/a&gt;. Du kan även läsa
	      en &lt;a class="ie6expl" href="http://mindpark.se/2009/02/18/heja-norge/"&gt;bakgrund
	      till uppmaningen på svenska här&lt;/a&gt;.
	    &lt;/p&gt;
	  &lt;/div&gt;
	  &lt;![endif]</xsl:comment>

<div id="innehallsforteckning">
	<ul id="toc">
	  <xsl:apply-templates mode="toc"/>
	</ul>
      </div>

      <div id="dokument">
	<xsl:apply-templates/>
      </div>

      <div id="sidfot">
        Sidfot
      </div>
      <script type="text/javascript"><xsl:comment>
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
      </xsl:comment></script>
      <script type="text/javascript"><xsl:comment>
var pageTracker = _gat._getTracker("UA-172287-1");
pageTracker._trackPageview();
      </xsl:comment></script>
    </body>
  </xsl:template>
  
</xsl:stylesheet>
