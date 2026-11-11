(() => {
  let initialized = false;
  let chartId = 0;
  let activeScheme = null;

  const readColor = (name, fallback) => {
    const value = getComputedStyle(document.body).getPropertyValue(name).trim();
    return value || fallback;
  };

  const themeVariables = () => {
    const scheme = document.body.getAttribute("data-md-color-scheme") || "purple";
    const dark = scheme === "slate";
    const colors = {
      base: readColor("--ot-base", dark ? "#1e1e2e" : "#eff1f5"),
      mantle: readColor("--ot-mantle", dark ? "#181825" : "#e6e9ef"),
      crust: readColor("--ot-crust", dark ? "#11111b" : "#dce0e8"),
      surface: readColor("--ot-surface", dark ? "#313244" : "#ccd0da"),
      surface2: readColor("--ot-overlay", dark ? "#45475a" : "#9ca0b0"),
      text: readColor("--ot-text", dark ? "#cdd6f4" : "#4c4f69"),
      subtext: readColor("--ot-subtext", dark ? "#a6adc8" : "#6c6f85"),
      lavender: readColor("--ot-lavender", dark ? "#cba6f7" : "#8839ef"),
      blue: readColor("--ot-blue", dark ? "#89b4fa" : "#1e66f5"),
      green: readColor("--ot-green", dark ? "#a6e3a1" : "#40a02b"),
      teal: readColor("--ot-teal", dark ? "#94e2d5" : "#179299"),
      pink: readColor("--ot-pink", dark ? "#f5c2e7" : "#ea76cb"),
      yellow: dark ? "#f9e2af" : "#df8e1d",
      peach: dark ? "#fab387" : "#fe640b",
      red: dark ? "#f38ba8" : "#d20f39",
    };

    const scale = [
      colors.lavender,
      colors.blue,
      colors.green,
      colors.pink,
      colors.teal,
      colors.yellow,
      colors.peach,
      colors.red,
    ];

    const variables = {
      darkMode: dark,
      background: "transparent",
      fontFamily: '"Cascadia Code", "Fira Code", monospace',
      fontSize: "16px",
      primaryColor: colors.surface,
      primaryTextColor: colors.text,
      primaryBorderColor: colors.lavender,
      secondaryColor: colors.surface2,
      secondaryTextColor: colors.text,
      secondaryBorderColor: colors.blue,
      tertiaryColor: colors.mantle,
      tertiaryTextColor: colors.text,
      tertiaryBorderColor: colors.green,
      lineColor: colors.blue,
      textColor: colors.text,
      mainBkg: colors.surface,
      nodeBorder: colors.lavender,
      nodeTextColor: colors.text,
      clusterBkg: colors.mantle,
      clusterBorder: colors.surface2,
      defaultLinkColor: colors.blue,
      edgeLabelBackground: colors.mantle,
      titleColor: colors.text,
      actorBkg: colors.surface,
      actorBorder: colors.blue,
      actorTextColor: colors.text,
      actorLineColor: colors.surface2,
      signalColor: colors.blue,
      signalTextColor: colors.text,
      labelBoxBkgColor: colors.surface,
      labelBoxBorderColor: colors.lavender,
      labelTextColor: colors.text,
      loopTextColor: colors.text,
      noteBkgColor: colors.mantle,
      noteBorderColor: colors.lavender,
      noteTextColor: colors.text,
      activationBkgColor: colors.surface,
      activationBorderColor: colors.blue,
      sequenceNumberColor: dark ? colors.crust : colors.base,
      pie1: colors.lavender,
      pie2: colors.blue,
      pie3: colors.green,
      pie4: colors.pink,
      pie5: colors.teal,
      pie6: colors.yellow,
      pie7: colors.peach,
      pie8: colors.red,
      pieTitleTextColor: colors.text,
      pieSectionTextColor: dark ? colors.crust : colors.base,
      pieLegendTextColor: colors.text,
      pieStrokeColor: dark ? colors.crust : colors.base,
      pieOuterStrokeColor: dark ? colors.crust : colors.base,
    };

    scale.forEach((color, index) => {
      variables[`cScale${index}`] = color;
      variables[`cScaleLabel${index}`] = dark ? colors.crust : colors.base;
    });

    return variables;
  };

  const initialize = () => {
    if (!window.mermaid) {
      return false;
    }

    window.mermaid.initialize({
      startOnLoad: false,
      theme: "base",
      themeVariables: themeVariables(),
      flowchart: {
        htmlLabels: true,
        curve: "basis",
        padding: 12,
        nodeSpacing: 40,
        rankSpacing: 50,
      },
      sequence: {
        actorFontSize: 16,
        messageFontSize: 16,
        noteFontSize: 16,
        useMaxWidth: true,
      },
      pie: {
        useMaxWidth: true,
        textPosition: 0.75,
      },
      timeline: {
        useMaxWidth: true,
        padding: 8,
      },
    });

    initialized = true;
    return true;
  };

  const renderSource = (source, id) => window.mermaid.render(id, source);

  const renderContainer = (container) => {
    const source = container.dataset.mermaidSource;
    if (!source) {
      return;
    }

    renderSource(source, `omarchy-mermaid-${chartId++}`)
      .then(({ svg }) => {
        container.innerHTML = svg;
        container.removeAttribute("data-mermaid-error");
      })
      .catch(() => {
        container.dataset.mermaidError = "true";
      });
  };

  const renderPending = () => {
    if (!window.mermaid) {
      return;
    }

    initialize();

    document.querySelectorAll("pre.mermaid-chart:not([data-mermaid-ready])").forEach((element) => {
      element.dataset.mermaidReady = "true";
      const source = element.textContent;
      const id = `omarchy-mermaid-${chartId++}`;

      renderSource(source, id)
        .then(({ svg }) => {
          const container = document.createElement("div");
          container.className = "mermaid";
          container.dataset.mermaidSource = source;
          container.innerHTML = svg;
          element.replaceWith(container);
        })
        .catch(() => {
          element.dataset.mermaidError = "true";
        });
    });
  };

  const refresh = () => {
    if (!window.mermaid) {
      return;
    }

    initialize();
    document.querySelectorAll(".mermaid[data-mermaid-source]").forEach(renderContainer);
  };

  const schemeChanged = () => {
    const scheme = document.body.getAttribute("data-md-color-scheme");
    if (scheme === activeScheme) {
      return;
    }

    activeScheme = scheme;
    if (initialized) {
      refresh();
    }
  };

  const start = () => {
    if (!window.mermaid) {
      window.setTimeout(start, 50);
      return;
    }

    activeScheme = document.body.getAttribute("data-md-color-scheme");
    initialize();
    renderPending();

    new MutationObserver(renderPending).observe(document.body, {
      childList: true,
      subtree: true,
    });

    new MutationObserver(schemeChanged).observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"],
    });
  };

  window.setTimeout(() => {
    document.querySelectorAll("pre.mermaid-chart:not([data-mermaid-error])").forEach((element) => {
      element.dataset.mermaidError = "true";
    });
  }, 15000);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
