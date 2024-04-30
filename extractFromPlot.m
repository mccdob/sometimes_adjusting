function demand  = extractFromPlot()

imdat = imread("image.png");
imshow(imdat);

xrange = ginput(2);
yrange = ginput(2);

plotData = ginput(24);

hold on
plot(xrange(1,1),xrange(1,2),'xr')
plot(xrange(2,1),xrange(2,2),'xr')
xscale = 24/(xrange(2,1)-xrange(1,1));  %Hours/pixel
plot(yrange(1,1),yrange(1,2),'xg')
plot(yrange(2,1),yrange(2,2),'xg')
yscale = 1200/(yrange(2,2)-yrange(1,2));    %Watts/Pixel

plot(plotData(:,1),plotData(:,2))
hold off

% Convert plotData into watts and hours
demand(:,1) = (plotData(:,1)-xrange(1,1))*xscale;
demand(:,2) = (plotData(:,2)-yrange(1,2))*yscale;

figure
plot(demand(:,1),demand(:,2))
xlim([0 24])
ylim([0 1200])