/* Dev Console (frontends/dev/index.html): sin logica propia, solo engancha
   los tooltips del glosario y el tour de demo. */
(function () {
  'use strict';
  if (window.initGlossaryTooltips) initGlossaryTooltips();
  if (window.DemoTour) DemoTour.run();
})();
