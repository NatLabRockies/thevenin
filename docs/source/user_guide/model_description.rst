Model Description
=================
This page outlines the underlying mathematics of the Thevenin equivalent circuit model. The index :math:`j` is used throughout the documentation to gernalize the fact that the model can be run with a variable number of resistor-capacitor (RC) elements. When zero RC pairs are specified, the model collapses into the simpler Rint model, discussed :doc:`here <equivalent_circuit_models>`. However, the model also allows any nonzero number of RC pairs, within reason. The figure below illustrates an example Thevenin circuit with two RC pairs.

.. figure:: figures/2RC_circuit.png
   :align: center
   :alt: Two-RC-pair Thevenin circuit.
   :width: 75%

The Thevenin circuit is governed by the evolution of the state of charge (SOC, -), hysteresis (:math:`h`, V), RC overpotentials (:math:`V_j`, V), cell voltage (:math:`V_{\rm cell}`, V), and temperature (:math:`T_{\rm cell}`, K). SOC and :math:`V_j` evolve in time as

.. math::

    \begin{align}
      &\frac{d\rm SOC}{dt} = \frac{-I \eta_{\rm ce}}{3600 Q_{\rm max}}, \\
      &\frac{dV_j}{dt} = -\frac{V_j}{R_jC_j} + \frac{I}{C_j},
    \end{align}

where :math:`I` is the load current (A), :math:`Q_{\rm max}` is the maximum nominal cell capacity (Ah), and :math:`R_j` and :math:`C_j` are the resistance (Ohm) and capacitance (F) of each RC pair :math:`j`. :math:`\eta_{\rm ce}` is the cell's Coulombic efficiency, which is always equal to unity during discharge. Note that the sign convention for :math:`I` is chosen such that positive :math:`I` discharges the battery (reduces SOC) and negative :math:`I` charges the battery (increases SOC). This convention is consistent with common physics-based models, e.g., the single particle model or pseudo-2D model. While not explicitly included in the equations above, :math:`R_j` and :math:`C_j` are functions of SOC and :math:`T_{\rm cell}`. 

The hysteresis only includes a dynamic component and neglects any instantaneous effects when switching between charging and discharging directions. The hysteresis dynamics are captured by 

.. math:: 

  \begin{equation}
    \frac{dh}{dt} = \bigg| \frac{\eta_{\rm ce} I \gamma}{3600 Q_{\rm max}} \bigg| \times (-{\rm sign}(I)M({\rm SOC}) - h),
  \end{equation}

The solution to this expression causes $h$ to exponentially decaying toward $-{\rm sign}(I)M({\rm SOC})$ at a rate determined by the leading coefficient. The approach rate can be controlled with the unitless parameter $\gamma$. The magnitude of hysteresis $M$ can be defined as a function of SOC for maximum flexibility. The constant or expression used for $M$ should always be positive. The model internally evaluates ${\rm sign}(I)$ to force $h$ to go toward positive and negative $M$ during charge and discharge events, respectively. When calibrating a model against a cell chemistry that has negligible hysteresis you can set both $\gamma$ and $M$ to zero.

The temperature increases while the cell is active according to

.. math:: 
    
    \begin{equation}
      mC_p\frac{dT_{\rm cell}}{dt} = \dot{Q}_{\rm gen} + \dot{Q}_{\rm conv},
    \end{equation}

where :math:`m` is mass (kg), :math:`C_p` is specific heat capacity (J/kg/K), :math:`\dot{Q}_{\rm gen}` is the heat generation (W), and :math:`\dot{Q}_{\rm conv}` is the convective heat loss (W). Heat generation and convection are defined by

.. math:: 

    \begin{align}
      &\dot{Q}_{\rm gen} = I \times (V_{\rm OCV}({\rm SOC}) + h - V_{\rm cell}), \\
      &\dot{Q}_{\rm conv} = h_TA(T_{\infty} - T_{\rm cell}),
    \end{align}

where :math:`h_T` is the convective heat transfer coefficient (W/m\ :sup:`2`/K), :math:`A` is heat loss area (m\ :sup:`2`), and :math:`T_{\infty}` is the air/room temperature (K). :math:`V_{\rm OCV}` is the open circuit voltage (V) and is a function of SOC.

The overall cell voltage is

.. math:: 

    \begin{equation}
      V_{\rm cell} = V_{\rm OCV}({\rm SOC}) + h - \sum_j V_j - IR_0,
    \end{equation}

where :math:`R_0` is the lone series resistance (Ohm), as shown in Figure 1. Just like the other resistive elements, :math:`R_0` is a function of SOC and :math:`T_{\rm cell}`.