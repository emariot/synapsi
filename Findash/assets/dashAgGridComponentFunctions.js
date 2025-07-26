var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

dagcomponentfuncs.DccGraphTooltip = function (props) {
    return React.createElement(
        window.dash_core_components.Graph,
        {
            figure: props.value,
            style: props.style || { width: "300px", height: "200px" },
            config: { displayModeBar: false }
        }
    );
};
